import * as THREE from "three";
import * as CANNON from "cannon-es";
import {DICE_MODELS, DICE_SHAPE} from "./upstream/DiceModels.js";

const Core = globalThis.Gravewright3DDiceCore;
const TAU = Math.PI * 2;
const DICE_ROUGHNESS_URL = "/sdk/packages/gravewright-3d-dice/asset/assets/roughnessMap_resin.webp";
// Dice So Nice's standard per-shape label scales. Keeping these fixed preserves
// its legibility without exposing the upstream appearance customizer.
const DSN_FONT_SCALE = {4: 1, 6: 1.3, 8: 1.1, 10: 1, 12: 1.1, 20: 1};

function roundedBoxGeometry(size, bevel, segments) {
    const inner = size / 2 - bevel;
    const geometry = new THREE.BoxGeometry(size, size, size, segments, segments, segments);
    const position = geometry.getAttribute("position");
    const vertex = new THREE.Vector3();
    for (let i = 0; i < position.count; i += 1) {
        vertex.fromBufferAttribute(position, i);
        const cx = THREE.MathUtils.clamp(vertex.x, -inner, inner);
        const cy = THREE.MathUtils.clamp(vertex.y, -inner, inner);
        const cz = THREE.MathUtils.clamp(vertex.z, -inner, inner);
        const dx = vertex.x - cx, dy = vertex.y - cy, dz = vertex.z - cz;
        const length = Math.hypot(dx, dy, dz);
        if (length > 1e-6) {
            const scale = bevel / length;
            position.setXYZ(i, cx + dx * scale, cy + dy * scale, cz + dz * scale);
        }
    }
    geometry.computeVertexNormals();
    return geometry;
}

function geometryFor(faces, radius) {
    const geometry = new THREE.BufferGeometryLoader().parse(DICE_MODELS[`d${faces}`]);
    geometry.computeBoundingSphere();
    const currentRadius = geometry.boundingSphere?.radius || radius;
    const shapeScale = faces === 4 ? 1.08 : faces === 6 ? 0.94 : faces === 10 ? 0.96 : 1;
    geometry.scale((radius * shapeScale) / currentRadius, (radius * shapeScale) / currentRadius, (radius * shapeScale) / currentRadius);
    geometry.computeBoundingSphere();
    geometry.computeVertexNormals();
    if (!geometry.getAttribute("uv")) {
        const position = geometry.getAttribute("position");
        const uv = new Float32Array(position.count * 2);
        for (let index = 0; index < position.count; index += 1) {
            const x = position.getX(index), y = position.getY(index), z = position.getZ(index);
            const length = Math.hypot(x, y, z) || 1;
            uv[index * 2] = 0.5 + Math.atan2(z, x) / TAU;
            uv[index * 2 + 1] = 0.5 - Math.asin(THREE.MathUtils.clamp(y / length, -1, 1)) / Math.PI;
        }
        geometry.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
    }
    return geometry;
}

function upstreamFaceAnchors(geometry, faces) {
    const renderFaces = planarFaces(geometry);
    const shape = DICE_SHAPE[`d${faces}`];
    const physicalFaces = shape.faces.map(face => {
        const indices = shape.skipLastFaceIndex ? face.slice(0, -1) : face;
        const points = indices.map(index => new THREE.Vector3(...shape.vertices[index]).normalize());
        const center = points.reduce((sum, point) => sum.add(point), new THREE.Vector3()).multiplyScalar(1 / points.length);
        const normal = new THREE.Vector3().crossVectors(
            points[1].clone().sub(points[0]),
            points[2].clone().sub(points[0]),
        ).normalize();
        if (normal.dot(center) < 0) normal.negate();
        return {normal, shapeVertexIndices: indices};
    });
    return physicalFaces.map(physicalFace => {
        const normal = physicalFace.normal;
        const ranked = renderFaces
            .map(candidate => ({candidate, alignment: candidate.normal.dot(normal)}))
            .sort((a, b) => b.alignment - a.alignment);
        const bestAlignment = ranked[0]?.alignment ?? -1;
        // Bevel triangles can have virtually the same normal as the numbered face.
        // Among coplanar matches, the largest inscribed area is the printable face.
        const anchor = ranked
            .filter(match => match.alignment >= bestAlignment - 0.002)
            .reduce((best, match) => match.candidate.faceRadius > best.faceRadius ? match.candidate : best, ranked[0].candidate);
        return {...anchor, shapeVertexIndices: physicalFace.shapeVertexIndices};
    });
}

function numeralTexture(label, color, faces, cache) {
    const cacheKey = `${faces}:${color}:${label}`;
    if (cache.has(cacheKey)) return cache.get(cacheKey);
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 1024;
    const context = canvas.getContext("2d");
    context.clearRect(0, 0, 1024, 1024);
    context.fillStyle = color;
    const shapeScale = DSN_FONT_SCALE[faces] || 1;
    let fontSize = (label.length > 1 ? 600 : 720) * shapeScale;
    context.font = `900 ${fontSize}px Inter, sans-serif`;
    const measuredWidth = context.measureText(label).width;
    if (measuredWidth > 800) {
        fontSize *= 800 / measuredWidth;
        context.font = `900 ${fontSize}px Inter, sans-serif`;
    }
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.lineJoin = "round";
    context.strokeStyle = color;
    context.lineWidth = 10;
    context.strokeText(label, 512, 516);
    context.fillText(label, 512, 516);
    if (label === "6" || label === "9") {
        context.strokeStyle = color;
        context.lineWidth = 30;
        context.lineCap = "round";
        context.beginPath();
        context.moveTo(410, 794);
        context.lineTo(614, 794);
        context.stroke();
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.magFilter = THREE.LinearFilter;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.anisotropy = 8;
    texture.needsUpdate = true;
    cache.set(cacheKey, texture);
    return texture;
}

function restD4OnFloor(mesh, geometry, floorY = -0.2) {
    const position = geometry.getAttribute("position");
    const vertex = new THREE.Vector3();
    let lowest = Infinity;
    for (let index = 0; index < position.count; index += 1) {
        vertex.fromBufferAttribute(position, index).applyQuaternion(mesh.quaternion);
        lowest = Math.min(lowest, vertex.y);
    }
    mesh.position.y = floorY - lowest + 0.012;
}

function planarFaces(geometry) {
    const position = geometry.getAttribute("position");
    const index = geometry.index;
    const groups = new Map();
    const triangleCount = index ? index.count / 3 : position.count / 3;
    const vertex = offset => {
        const i = index ? index.getX(offset) : offset;
        return new THREE.Vector3(position.getX(i), position.getY(i), position.getZ(i));
    };
    for (let triangle = 0; triangle < triangleCount; triangle += 1) {
        const a = vertex(triangle * 3);
        const b = vertex(triangle * 3 + 1);
        const c = vertex(triangle * 3 + 2);
        const normal = new THREE.Vector3().crossVectors(b.clone().sub(a), c.clone().sub(a)).normalize();
        const center = a.clone().add(b).add(c).multiplyScalar(1 / 3);
        if (normal.dot(center) < 0) normal.negate();
        const key = `${normal.x.toFixed(3)},${normal.y.toFixed(3)},${normal.z.toFixed(3)},${normal.dot(center).toFixed(3)}`;
        const face = groups.get(key) || {normal, centers: [], points: []};
        face.centers.push(center);
        face.points.push(a, b, c);
        groups.set(key, face);
    }
    return [...groups.values()].map(face => {
        const center = face.centers.reduce((sum, value) => sum.add(value), new THREE.Vector3()).multiplyScalar(1 / face.centers.length);
        const faceRadius = Math.min(...face.points.map(point => point.distanceTo(center)));
        const points = [...new Map(face.points.map(point => [`${point.x.toFixed(5)},${point.y.toFixed(5)},${point.z.toFixed(5)}`, point])).values()];
        return {normal: face.normal, center, faceRadius, points};
    });
}

function cannonShape(geometry) {
    const vertices = [];
    const vertexMap = new Map();
    const indexFor = point => {
        const key = `${point.x.toFixed(5)},${point.y.toFixed(5)},${point.z.toFixed(5)}`;
        if (!vertexMap.has(key)) {
            vertexMap.set(key, vertices.length);
            vertices.push(new CANNON.Vec3(point.x, point.y, point.z));
        }
        return vertexMap.get(key);
    };
    const faces = planarFaces(geometry).map(face => {
        const reference = Math.abs(face.normal.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
        const u = new THREE.Vector3().crossVectors(reference, face.normal).normalize();
        const v = new THREE.Vector3().crossVectors(face.normal, u).normalize();
        const ordered = [...face.points].sort((a, b) => {
            const aa = a.clone().sub(face.center);
            const bb = b.clone().sub(face.center);
            return Math.atan2(aa.dot(v), aa.dot(u)) - Math.atan2(bb.dot(v), bb.dot(u));
        });
        const outward = new THREE.Vector3().crossVectors(ordered[1].clone().sub(ordered[0]), ordered[2].clone().sub(ordered[0]));
        if (outward.dot(face.normal) < 0) ordered.reverse();
        return ordered.map(indexFor);
    });
    return new CANNON.ConvexPolyhedron({vertices, faces});
}

function faceLabels(mesh, geometry, die, color, radius, textureCache) {
    const anchors = upstreamFaceAnchors(geometry, die.faces);
    const shapeValues = DICE_SHAPE[`d${die.faces}`].faceValues;
    const values = shapeValues.map(value => die.percentile === "tens"
        ? String((value === 10 ? 0 : value) * 10).padStart(2, "0")
        : String(value === 10 && die.faces === 10 ? 0 : value));
    if (die.faces === 4) {
        const d4Vertices = DICE_SHAPE.d4.vertices.map(vertex => new THREE.Vector3(...vertex).normalize());
        const labels = [];
        anchors.forEach(anchor => {
            anchor.shapeVertexIndices.forEach(vertexIndex => {
                const texture = numeralTexture(String(vertexIndex + 1), color, 4, textureCache);
                const material = new THREE.MeshBasicMaterial({map: texture, transparent: true, alphaTest: 0.12, depthWrite: true, side: THREE.FrontSide, polygonOffset: true, polygonOffsetFactor: -4});
                const shapeVertex = d4Vertices[vertexIndex];
                const faceVertex = anchor.points.reduce((best, point) =>
                    point.clone().normalize().dot(shapeVertex) > best.clone().normalize().dot(shapeVertex) ? point : best,
                anchor.points[0]);
                const radial = faceVertex.clone().sub(anchor.center).normalize();
                const xAxis = new THREE.Vector3().crossVectors(radial, anchor.normal).normalize();
                const orientation = new THREE.Matrix4().makeBasis(xAxis, radial, anchor.normal);
                const label = new THREE.Mesh(
                    new THREE.PlaneGeometry(Math.min(radius * 0.38, anchor.faceRadius * 0.55), Math.min(radius * 0.38, anchor.faceRadius * 0.55)),
                    material,
                );
                label.position.copy(anchor.center).lerp(faceVertex, 0.55).addScaledVector(anchor.normal, radius * 0.018);
                label.quaternion.setFromRotationMatrix(orientation);
                label.renderOrder = 3;
                mesh.add(label);
                labels.push({mesh: label, material, texture});
            });
        });
        return {labels, anchors, targetIndex: Number(die.result) - 1, d4Vertices};
    }
    const labels = anchors.map((anchor, index) => {
        const texture = numeralTexture(values[index], color, die.faces, textureCache);
        const material = new THREE.MeshBasicMaterial({map: texture, transparent: true, alphaTest: 0.12, depthWrite: true, side: THREE.FrontSide, polygonOffset: true, polygonOffsetFactor: -4});
        const radiusScale = ({4: 0.68, 6: 0.72, 8: 0.66, 10: 0.68, 12: 0.72, 20: 0.66})[die.faces] || 0.66;
        const faceScale = ({4: 1.08, 6: 1.04, 8: 1.12, 10: 1.12, 12: 1.14, 20: 1.16})[die.faces] || 1.08;
        const size = Math.min(radius * radiusScale, anchor.faceRadius * faceScale);
        const label = new THREE.Mesh(new THREE.PlaneGeometry(size, size), material);
        label.position.copy(anchor.center).addScaledVector(anchor.normal, radius * 0.018);
        label.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), anchor.normal);
        label.renderOrder = 3;
        mesh.add(label);
        return {mesh: label, material, texture};
    });
    const targetValue = die.percentile === "tens"
        ? (Number(die.result) === 0 ? 10 : Number(die.result) / 10)
        : (die.faces === 10 && Number(die.result) === 0 ? 10 : Number(die.result));
    const targetIndex = Math.max(0, shapeValues.indexOf(targetValue));
    return {labels, anchors, targetIndex};
}

function upstreamCannonShape(faces, radius) {
    const shape = DICE_SHAPE[`d${faces}`];
    const vertices = shape.vertices.map(vertex => {
        const length = Math.hypot(...vertex) || 1;
        return new CANNON.Vec3(vertex[0] * radius / length, vertex[1] * radius / length, vertex[2] * radius / length);
    });
    const physicalFaces = shape.faces.map(face => shape.skipLastFaceIndex ? face.slice(0, -1) : [...face]);
    return new CANNON.ConvexPolyhedron({vertices, faces: physicalFaces});
}

// These dimensions follow the visible inner leather edge of dice-tray-top-down.png.
// Keeping the render and physics in the same orthographic coordinate system prevents
// dice from appearing to pass underneath the diagonal rails.
const TRAY_HALF_WIDTH = 3.88, TRAY_HALF_DEPTH = 3.08, TRAY_CORNER_CUT_X = 1.08, TRAY_CORNER_CUT_Z = 1.0;
const TRAY_CORNERS = [
    [TRAY_HALF_WIDTH - TRAY_CORNER_CUT_X, -TRAY_HALF_DEPTH], [TRAY_HALF_WIDTH, -TRAY_HALF_DEPTH + TRAY_CORNER_CUT_Z],
    [TRAY_HALF_WIDTH, TRAY_HALF_DEPTH - TRAY_CORNER_CUT_Z], [TRAY_HALF_WIDTH - TRAY_CORNER_CUT_X, TRAY_HALF_DEPTH],
    [-(TRAY_HALF_WIDTH - TRAY_CORNER_CUT_X), TRAY_HALF_DEPTH], [-TRAY_HALF_WIDTH, TRAY_HALF_DEPTH - TRAY_CORNER_CUT_Z],
    [-TRAY_HALF_WIDTH, -TRAY_HALF_DEPTH + TRAY_CORNER_CUT_Z], [-(TRAY_HALF_WIDTH - TRAY_CORNER_CUT_X), -TRAY_HALF_DEPTH],
];
const TRAY_BOUNDARY = TRAY_CORNERS.map((point, index) => {
    const next = TRAY_CORNERS[(index + 1) % TRAY_CORNERS.length];
    const edgeX = next[0] - point[0], edgeZ = next[1] - point[1];
    const length = Math.hypot(edgeZ, -edgeX) || 1;
    let nx = edgeZ / length, nz = -edgeX / length;
    if (nx * (0 - point[0]) + nz * (0 - point[1]) < 0) { nx = -nx; nz = -nz; }
    return {x: point[0], z: point[1], nx, nz};
});

function buildTrayWalls(world, material) {
    const thickness = 0.48, height = 2.8, wallY = 1.1;
    return TRAY_CORNERS.map((start, index) => {
        const [x1, z1] = start;
        const [x2, z2] = TRAY_CORNERS[(index + 1) % TRAY_CORNERS.length];
        const dx = x2 - x1, dz = z2 - z1;
        const length = Math.hypot(dx, dz);
        const body = new CANNON.Body({mass: 0, shape: new CANNON.Box(new CANNON.Vec3(thickness / 2, height / 2, (length + thickness) / 2)), material});
        body.position.set((x1 + x2) / 2, wallY, (z1 + z2) / 2);
        body.quaternion.setFromEuler(0, Math.atan2(dx, dz), 0);
        world.addBody(body);
        return body;
    });
}

function clampToTray(body, margin) {
    let impacted = false;
    // Project repeatedly because correcting one side near a clipped corner can
    // move the sphere outside its neighbouring side.
    for (let iteration = 0; iteration < 4; iteration += 1) {
        let corrected = false;
        for (const edge of TRAY_BOUNDARY) {
            const distance = (body.position.x - edge.x) * edge.nx + (body.position.z - edge.z) * edge.nz;
            if (distance < margin) {
                impacted = true;
                corrected = true;
                const push = margin - distance;
                body.position.x += edge.nx * push;
                body.position.z += edge.nz * push;
                const outward = body.velocity.x * edge.nx + body.velocity.z * edge.nz;
                if (outward < 0) {
                    body.velocity.x -= outward * edge.nx;
                    body.velocity.z -= outward * edge.nz;
                }
            }
        }
        if (!corrected) break;
    }
    return impacted;
}

export class DiceRenderer {
    constructor(host) {
        this.host = host;
        const shell = host.firstElementChild;
        this.container = shell?.classList.contains("gravewright-3d-dice")
            ? shell
            : document.createElement("div");
        this.container.className = "gravewright-3d-dice";
        this.container.dataset.testid = "gravewright-3d-dice";
        this.tray = document.createElement("div");
        this.tray.className = "gravewright-3d-dice-tray";
        this.tray.hidden = true;
        this.status = document.createElement("output");
        this.status.className = "gravewright-3d-dice-status";
        this.status.setAttribute("aria-live", "polite");
        this.container.append(this.tray, this.status);
        if (!this.container.isConnected) host.appendChild(this.container);
        this.queue = [];
        this.active = [];
        this.frame = 0;
        this.wakeTimer = 0;
        this.preparing = false;
        this.destroyed = false;
        this.metrics = {frames: 0, totalFrameMs: 0, maxFrameMs: 0, spawned: 0, cleaned: 0};
        this.reducedMotion = Boolean(globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
        this.typographyReady = !document.fonts;
        if (document.fonts) {
            document.fonts.load('850 32px Inter', "0123456789").then(() => {
                this.typographyReady = true;
                this.pump();
            }).catch(() => {
                this.typographyReady = true;
                this.pump();
            });
        }
        this.setupThree();
        this.setupPhysics();
        this.resizeObserver = new ResizeObserver(() => this.resize());
        this.resizeObserver.observe(this.container);
        this.resize();
        this.syncStatus();
    }

    setupThree() {
        this.scene = new THREE.Scene();
        this.camera = new THREE.OrthographicCamera(-8, 8, 4.8, -4.8, 0.1, 50);
        this.camera.position.set(0, 14, 0);
        this.camera.up.set(0, 0, -1);
        this.camera.lookAt(0, 0, 0);
        try {
            this.renderer = new THREE.WebGLRenderer({alpha: true, antialias: true, powerPreference: "high-performance"});
        } catch (_) {
            this.renderer = null;
            return;
        }
        this.renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio || 1, 1.7));
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.domElement.setAttribute("aria-hidden", "true");
        this.container.insertBefore(this.renderer.domElement, this.status);
        this.diceRoughnessTexture = new THREE.TextureLoader().load(DICE_ROUGHNESS_URL);
        this.diceRoughnessTexture.colorSpace = THREE.NoColorSpace;
        this.diceRoughnessTexture.wrapS = THREE.RepeatWrapping;
        this.diceRoughnessTexture.wrapT = THREE.RepeatWrapping;
        this.diceRoughnessTexture.anisotropy = Math.min(8, this.renderer.capabilities.getMaxAnisotropy());
        this.scene.add(new THREE.HemisphereLight(0xffe3bd, 0x11141c, 2.1));
        const key = new THREE.DirectionalLight(0xffd39a, 3.2);
        key.position.set(-4, 9, 3);
        key.castShadow = true;
        key.shadow.mapSize.set(1024, 1024);
        this.scene.add(key);
        const floor = new THREE.Mesh(new THREE.PlaneGeometry(11.6, 7.2), new THREE.ShadowMaterial({opacity: 0.34}));
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -0.18;
        floor.receiveShadow = true;
        this.scene.add(floor);
    }

    setupPhysics() {
        this.world = new CANNON.World({gravity: new CANNON.Vec3(0, -22, 0)});
        this.world.allowSleep = true;
        this.world.solver.iterations = 18;
        this.world.broadphase = new CANNON.SAPBroadphase(this.world);
        this.world.defaultContactMaterial.friction = 0.12;
        this.world.defaultContactMaterial.restitution = 0.3;
        this.diceMaterial = new CANNON.Material("die");
        const floorMaterial = new CANNON.Material("floor");
        const wallMaterial = new CANNON.Material("wall");
        this.world.addContactMaterial(new CANNON.ContactMaterial(this.diceMaterial, floorMaterial, {friction: 0.08, restitution: 0.28}));
        this.world.addContactMaterial(new CANNON.ContactMaterial(this.diceMaterial, wallMaterial, {friction: 0.1, restitution: 0.42}));
        this.world.addContactMaterial(new CANNON.ContactMaterial(this.diceMaterial, this.diceMaterial, {friction: 0.12, restitution: 0.46}));
        const floor = new CANNON.Body({mass: 0, shape: new CANNON.Plane(), material: floorMaterial});
        floor.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
        floor.position.y = -0.2;
        this.world.addBody(floor);
        this.staticBodies = [floor, ...buildTrayWalls(this.world, wallMaterial)];
    }

    resize() {
        const width = Math.max(1, this.container.clientWidth || this.host.clientWidth || 800);
        const height = Math.max(1, this.container.clientHeight || this.host.clientHeight || 600);
        this.width = width;
        this.height = height;
        if (!this.renderer) return;
        this.renderer.setSize(width, height, false);
        const halfHeight = 4.8;
        const halfWidth = halfHeight * (width / height);
        this.camera.left = -halfWidth;
        this.camera.right = halfWidth;
        this.camera.top = halfHeight;
        this.camera.bottom = -halfHeight;
        this.camera.updateProjectionMatrix();
    }

    enqueue(sequence) {
        if (this.destroyed || !this.renderer || !sequence.dice.length) return false;
        if (this.queue.length >= 32) this.queue.shift();
        this.queue.push(sequence);
        if (this.wakeTimer) {
            clearTimeout(this.wakeTimer);
            this.wakeTimer = 0;
        }
        this.pump();
        return true;
    }

    pump() {
        if (this.destroyed || !this.typographyReady) return;
        if (!this.preparing && this.active.length < 8 && this.queue.length) {
            this.preparing = true;
            void this.spawn(this.queue.shift()).finally(() => {
                this.preparing = false;
                this.pump();
            });
        }
        if (!this.frame && this.active.length && !this.wakeTimer) {
            const now = performance.now();
            const needsFrame = this.active.some(batch => {
                const elapsed = now - batch.start;
                const fadeStart = batch.motion * 0.76 + batch.hold;
                return elapsed < batch.motion || elapsed >= fadeStart;
            });
            if (needsFrame) this.frame = requestAnimationFrame(time => this.tick(time));
            else {
                const delay = Math.max(0, Math.min(...this.active.map(batch =>
                    batch.start + batch.motion * 0.76 + batch.hold - now,
                )));
                this.wakeTimer = setTimeout(() => {
                    this.wakeTimer = 0;
                    this.pump();
                }, delay);
            }
        }
    }

    async spawn(sequence) {
        this.tray.hidden = false;
        const motion = this.reducedMotion ? 1000 : 2200;
        const hold = this.reducedMotion ? 3500 : 3300;
        const fade = 650;
        const radius = Math.max(0.26, Math.min(0.62, 2.05 / Math.sqrt(Math.max(1, sequence.dice.length))));
        const numeral = Core.normalizeColor(sequence.fontColor || Core.numeralColor(sequence.color));
        const directionSeed = [...String(sequence.id)].reduce((sum, character) => ((sum * 31) + character.charCodeAt(0)) >>> 0, 17);
        const directions = [
            {origin: [0, 2.5], inward: [0, -1]}, {origin: [0, -2.5], inward: [0, 1]},
            {origin: [-3.25, 0], inward: [1, 0]}, {origin: [3.25, 0], inward: [-1, 0]},
            {origin: [-2.55, 1.85], inward: [0.78, -0.62]}, {origin: [2.55, 1.85], inward: [-0.78, -0.62]},
            {origin: [-2.55, -1.85], inward: [0.78, 0.62]}, {origin: [2.55, -1.85], inward: [-0.78, 0.62]},
        ];
        const throwDirection = directions[directionSeed % directions.length];
        const numeralTextures = new Map();
        const objects = sequence.dice.map((die, index) => {
            const geometry = geometryFor(die.faces, radius);
            geometry.computeVertexNormals();
            const material = new THREE.MeshPhysicalMaterial({color: sequence.color, roughnessMap: this.diceRoughnessTexture, emissive: sequence.color, emissiveIntensity: 0.018, roughness: 0.3, metalness: 0.02, clearcoat: 0.5, clearcoatRoughness: 0.22, flatShading: false});
            const mesh = new THREE.Mesh(geometry, material);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry, die.faces === 6 ? 80 : 22), new THREE.LineBasicMaterial({color: 0x171b22, transparent: true, opacity: die.faces === 6 ? 0.12 : 0.3}));
            mesh.add(edges);
            const faceData = faceLabels(mesh, geometry, die, numeral, radius, numeralTextures);
            geometry.computeBoundingSphere();
            const collisionRadius = geometry.boundingSphere?.radius || radius;
            this.scene.add(mesh);
            const body = new CANNON.Body({mass: 1, shape: upstreamCannonShape(die.faces, collisionRadius), material: this.diceMaterial, linearDamping: 0.14, angularDamping: 0.18});
            const lane = ((index + 0.5) / sequence.dice.length - 0.5) * Math.min(4.8, sequence.dice.length * radius * 1.65);
            const tangent = [-throwDirection.inward[1], throwDirection.inward[0]];
            const scatter = (((directionSeed >>> (index % 16)) & 7) - 3) * 0.13;
            body.position.set(
                throwDirection.origin[0] + tangent[0] * lane,
                1.0 + (index % 3) * radius * 0.5,
                throwDirection.origin[1] + tangent[1] * lane,
            );
            body.velocity.set(
                throwDirection.inward[0] * (14.2 + (index % 4) * 0.45) + tangent[0] * scatter,
                1.2 + (index % 3) * 0.24,
                throwDirection.inward[1] * (14.2 + (index % 4) * 0.45) + tangent[1] * scatter,
            );
            body.angularVelocity.set(7 + index * 0.11, 9 - index * 0.05, 6 + index * 0.07);
            body.sleepSpeedLimit = 0.12;
            body.sleepTimeLimit = 0.35;
            this.world.addBody(body);
            // Dice enter from a launch cup placed against the selected tray wall.
            // Treat that initial wall contact as an impact; later contacts reinforce it.
            const state = {hitWall: true};
            body.addEventListener("collide", event => {
                if (event.body && event.body !== this.staticBodies[0] && event.body.mass === 0) state.hitWall = true;
            });
            return {...die, mesh, body, geometry, material, edgeGeometry: edges.geometry, edgeMaterial: edges.material, radius, collisionRadius, state, ...faceData};
        });
        await this.prepareFaceSwaps(objects);
        if (this.destroyed) {
            objects.forEach(object => this.disposeObject(object));
            numeralTextures.forEach(texture => texture.dispose());
            return;
        }
        // Pre-simulation is synchronous and can be noticeable for large pools.
        // Start the visible clock only after the complete trajectory is ready,
        // otherwise the first rendered frame may already be the final result.
        const animationStart = performance.now();
        this.active.push({id: sequence.id, color: sequence.color, objects, numeralTextures, start: animationStart, previous: animationStart, motion, hold, fade, dismissed: false});
        this.metrics.spawned += objects.length;
        this.syncStatus();
    }

    async prepareFaceSwaps(objects) {
        // Precompute in an isolated world. Yielding between small chunks keeps the
        // board, audio and controls responsive even for very large dice pools.
        const world = new CANNON.World({gravity: new CANNON.Vec3(0, -22, 0)});
        world.allowSleep = true;
        world.solver.iterations = 18;
        world.broadphase = new CANNON.SAPBroadphase(world);
        const diceMaterial = new CANNON.Material("trajectory-die");
        const floorMaterial = new CANNON.Material("trajectory-floor");
        const wallMaterial = new CANNON.Material("trajectory-wall");
        world.addContactMaterial(new CANNON.ContactMaterial(diceMaterial, floorMaterial, {friction: 0.08, restitution: 0.28}));
        world.addContactMaterial(new CANNON.ContactMaterial(diceMaterial, wallMaterial, {friction: 0.1, restitution: 0.42}));
        world.addContactMaterial(new CANNON.ContactMaterial(diceMaterial, diceMaterial, {friction: 0.12, restitution: 0.46}));
        const floor = new CANNON.Body({mass: 0, shape: new CANNON.Plane(), material: floorMaterial});
        floor.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
        floor.position.y = -0.2;
        world.addBody(floor);
        buildTrayWalls(world, wallMaterial);
        const simulationBodies = objects.map(object => {
            const source = object.body;
            const body = new CANNON.Body({
                mass: 1, shape: source.shapes[0], material: diceMaterial,
                linearDamping: source.linearDamping, angularDamping: source.angularDamping,
            });
            body.position.copy(source.position);
            body.quaternion.copy(source.quaternion);
            body.velocity.copy(source.velocity);
            body.angularVelocity.copy(source.angularVelocity);
            body.sleepSpeedLimit = source.sleepSpeedLimit;
            body.sleepTimeLimit = source.sleepTimeLimit;
            world.addBody(body);
            return body;
        });
        objects.forEach(object => { object.simulation = []; });
        for (let step = 0; step < 420; step += 1) {
            world.step(1 / 120);
            objects.forEach((object, index) => clampToTray(simulationBodies[index], object.collisionRadius * 1.03));
            objects.forEach((object, index) => object.simulation.push({
                position: [simulationBodies[index].position.x, simulationBodies[index].position.y, simulationBodies[index].position.z],
                quaternion: [simulationBodies[index].quaternion.x, simulationBodies[index].quaternion.y, simulationBodies[index].quaternion.z, simulationBodies[index].quaternion.w],
            }));
            if (step % 20 === 19) await new Promise(resolve => setTimeout(resolve, 0));
        }
        objects.forEach((object, index) => {
            const finalRotation = new THREE.Quaternion(
                simulationBodies[index].quaternion.x,
                simulationBodies[index].quaternion.y,
                simulationBodies[index].quaternion.z,
                simulationBodies[index].quaternion.w,
            );
            if (object.faces === 4) {
                let visibleVertex = 0;
                let visibleHeight = -Infinity;
                object.d4Vertices.forEach((vertex, index) => {
                    const height = vertex.clone().applyQuaternion(finalRotation).y;
                    if (height > visibleHeight) { visibleHeight = height; visibleVertex = index; }
                });
                object.faceSwap = new THREE.Quaternion().setFromUnitVectors(
                    object.d4Vertices[object.targetIndex],
                    object.d4Vertices[visibleVertex],
                );
                return;
            }
            let visibleIndex = 0;
            let visibleDot = -Infinity;
            object.anchors.forEach((anchor, index) => {
                const dot = anchor.normal.clone().applyQuaternion(finalRotation).y;
                if (dot > visibleDot) {
                    visibleDot = dot;
                    visibleIndex = index;
                }
            });
            object.faceSwap = new THREE.Quaternion().setFromUnitVectors(
                object.anchors[object.targetIndex].normal,
                object.anchors[visibleIndex].normal,
            );
        });
        objects.forEach(object => {
            object.body.type = CANNON.Body.KINEMATIC;
            object.body.updateMassProperties();
        });
    }

    tick(now) {
        this.frame = 0;
        if (this.destroyed || !this.renderer) return;
        const started = performance.now();
        const remaining = [];
        for (const batch of this.active) {
            const elapsed = now - batch.start;
            if (elapsed >= batch.motion + batch.hold + batch.fade) {
                batch.objects.forEach(object => this.disposeObject(object));
                batch.numeralTextures.forEach(texture => texture.dispose());
                this.metrics.cleaned += batch.objects.length;
                continue;
            }
            this.updateBatch(batch, elapsed);
            remaining.push(batch);
        }
        this.active = remaining;
        this.renderer.render(this.scene, this.camera);
        this.syncStatus();
        const frameMs = performance.now() - started;
        this.metrics.frames += 1;
        this.metrics.totalFrameMs += frameMs;
        this.metrics.maxFrameMs = Math.max(this.metrics.maxFrameMs, frameMs);
        this.pump();
    }

    updateBatch(batch, elapsed) {
        const settling = Math.min(1, elapsed / batch.motion);
        const fadeStart = batch.motion * 0.76 + batch.hold;
        batch.dismissed = elapsed >= fadeStart;
        const alpha = elapsed > fadeStart ? Math.max(0, 1 - (elapsed - fadeStart) / batch.fade) : 1;
        batch.objects.forEach(object => {
            const simulationIndex = Math.min(
                object.simulation.length - 1,
                Math.floor(settling * object.simulation.length),
            );
            const simulated = object.simulation[Math.max(0, simulationIndex)];
            object.body.position.set(...simulated.position);
            object.body.quaternion.set(...simulated.quaternion);
            const mayReveal = object.state.hitWall && settling >= 0.76;
            if (mayReveal && !object.frozen) {
                object.frozen = true;
            }
            object.mesh.position.copy(object.body.position);
            object.mesh.quaternion.copy(object.body.quaternion);
            object.mesh.quaternion.multiply(object.faceSwap);
            if (settling >= 0.995 && object.faces === 4) restD4OnFloor(object.mesh, object.geometry);
            if (settling >= 1 && !object.physicsReleased) {
                this.world.removeBody(object.body);
                object.physicsReleased = true;
                object.simulation = [simulated];
            }
            object.material.opacity = alpha;
            object.material.transparent = alpha < 1;
            object.labels.forEach(label => { label.material.opacity = alpha; });
            object.finalVisible = mayReveal;
        });
    }

    disposeObject(object) {
        if (!object.physicsReleased) this.world.removeBody(object.body);
        this.scene.remove(object.mesh);
        object.geometry.dispose();
        object.material.dispose();
        object.edgeGeometry.dispose();
        object.edgeMaterial.dispose();
        object.labels.forEach(label => {
            label.mesh.geometry.dispose();
            label.material.dispose();
        });
    }

    syncStatus() {
        const dice = this.active.flatMap(batch => batch.objects);
        const physicsBodies = dice.filter(die => !die.physicsReleased).length;
        const allBatchesDismissed = this.active.length > 0 && this.active.every(batch => batch.dismissed);
        this.tray.hidden = (dice.length === 0 && this.queue.length === 0)
            || (allBatchesDismissed && this.queue.length === 0);
        this.container.dataset.activeDice = String(dice.length);
        this.container.dataset.physicsBodies = String(physicsBodies);
        this.container.dataset.queuedRolls = String(this.queue.length);
        this.container.dataset.results = dice.map(die => `${die.faces}:${die.result}`).join(",");
        this.container.dataset.finalResults = dice.filter(die => die.finalVisible).map(die => `${die.faces}:${die.result}`).join(",");
        this.container.dataset.colors = this.active.map(batch => batch.color).join(",");
        this.container.dataset.wallImpacts = String(dice.filter(die => die.state.hitWall).length);
        this.container.dataset.frames = String(this.metrics.frames);
        this.container.dataset.averageFrameMs = String(this.metrics.frames ? this.metrics.totalFrameMs / this.metrics.frames : 0);
        this.container.dataset.maxFrameMs = String(this.metrics.maxFrameMs);
        this.status.textContent = dice.length ? `${dice.length} animated dice` : "";
    }

    snapshot() {
        const activeDice = this.active.reduce((sum, batch) => sum + batch.objects.length, 0);
        const physicsBodies = this.active.reduce((sum, batch) => sum + batch.objects.filter(object => !object.physicsReleased).length, 0);
        return Object.freeze({activeDice, physicsBodies, queuedRolls: this.queue.length, animationCallbacks: this.frame || this.wakeTimer ? 1 : 0, metrics: Object.freeze({...this.metrics, averageFrameMs: this.metrics.frames ? this.metrics.totalFrameMs / this.metrics.frames : 0})});
    }

    destroy() {
        if (this.destroyed) return;
        this.destroyed = true;
        if (this.frame) cancelAnimationFrame(this.frame);
        if (this.wakeTimer) clearTimeout(this.wakeTimer);
        this.frame = 0;
        this.wakeTimer = 0;
        this.queue.length = 0;
        this.active.forEach(batch => {
            batch.objects.forEach(object => this.disposeObject(object));
            batch.numeralTextures.forEach(texture => texture.dispose());
        });
        this.active.length = 0;
        this.staticBodies.forEach(body => this.world.removeBody(body));
        this.resizeObserver.disconnect();
        this.renderer?.dispose();
        this.diceRoughnessTexture?.dispose();
        this.renderer?.domElement.remove();
        this.container.remove();
        this.renderer = null;
    }
}
