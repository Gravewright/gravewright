







import { Editor, Node, Extension, mergeAttributes } from "https://esm.sh/@tiptap/core@2.11.5";
import StarterKit from "https://esm.sh/@tiptap/starter-kit@2.11.5";
import Placeholder from "https://esm.sh/@tiptap/extension-placeholder@2.11.5";
import Link from "https://esm.sh/@tiptap/extension-link@2.11.5";
import Suggestion from "https://esm.sh/@tiptap/suggestion@2.11.5";

const DOC_FORMAT = "gw-journal-doc-v1";
const DOC_VERSION = 1;

const EMPTY_PM_DOC = { type: "doc", content: [{ type: "paragraph" }] };

function wrapDoc(pmDoc) {
  return { format: DOC_FORMAT, version: DOC_VERSION, doc: pmDoc || { type: "doc", content: [] } };
}

function pmContentFrom(document) {
  const doc = document && document.doc;
  if (doc && doc.type === "doc" && Array.isArray(doc.content) && doc.content.length) {
    return doc;
  }
  return EMPTY_PM_DOC;
}



const GwCallout = Node.create({
  name: "gwCallout",
  group: "block",
  content: "block+",
  defining: true,

  addAttributes() {
    return {
      kind: { default: "gm_note" },
      visibility: { default: "gm" },
      title: { default: "" },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-gw-callout]' }];
  },

  renderHTML({ node, HTMLAttributes }) {
    const kind = node.attrs.kind === "secret" ? "secret" : "gm_note";
    return [
      "div",
      mergeAttributes(HTMLAttributes, {
        "data-gw-callout": kind,
        "data-visibility": "gm",
        class: `gw-callout gw-callout--${kind}`,
      }),
      [
        "div",
        { class: "gw-callout-label", contenteditable: "false" },
        node.attrs.title || (kind === "secret" ? "Segredo" : "Nota do GM"),
      ],
      ["div", { class: "gw-callout-body" }, 0],
    ];
  },
});


const GwImage = Node.create({
  name: "gwImage",
  group: "block",
  atom: true,
  draggable: true,
  selectable: true,

  addAttributes() {
    return {
      visibility: { default: "public" },
      assetId: { default: "" },
      src: { default: "" },
      alt: { default: "" },
      caption: { default: "" },
      align: { default: "center" },
      width: { default: null },
    };
  },

  parseHTML() {
    return [{ tag: "figure[data-gw-image] img" }, { tag: "img[data-gw-image]" }];
  },

  renderHTML({ node }) {
    const align = ["left", "center", "right"].includes(node.attrs.align) ? node.attrs.align : "center";
    const img = {
      src: node.attrs.src,
      alt: node.attrs.alt || "",
      "data-gw-image": "",
      "data-asset-id": node.attrs.assetId || "",
    };
    if (node.attrs.width) img.width = node.attrs.width;
    const figure = ["figure", { "data-gw-image": "", class: `gw-image gw-image--${align}` }, ["img", img]];
    if (node.attrs.caption) figure.push(["figcaption", {}, node.attrs.caption]);
    return figure;
  },
});


function pickImageFile(onPick) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/png,image/jpeg,image/webp";
  input.style.display = "none";
  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (file) onPick(file);
    input.remove();
  });
  document.body.appendChild(input);
  input.click();
}

async function insertImage(editor, file, uploadImage) {
  if (!uploadImage || !file) return;
  let asset;
  try {
    asset = await uploadImage(file);
  } catch {
    return;
  }
  if (asset && asset.src && asset.asset_id) {
    editor
      .chain()
      .focus()
      .insertContent({
        type: "gwImage",
        attrs: {
          visibility: "public",
          assetId: asset.asset_id,
          src: asset.src,
          alt: asset.alt || "",
          caption: "",
          align: "center",
          width: asset.width || null,
        },
      })
      .run();
  }
}




function buildCommands(labels, uploadImage) {
  const list = [
    { id: "text", group: labels.group_basic, label: labels.text, aliases: ["texto", "paragraph", "p"],
      run: ({ editor, range }) => editor.chain().focus().deleteRange(range).setParagraph().run() },
    { id: "h1", group: labels.group_basic, label: labels.heading1, aliases: ["titulo", "heading", "h1", "#"],
      run: ({ editor, range }) => editor.chain().focus().deleteRange(range).setNode("heading", { level: 1 }).run() },
    { id: "h2", group: labels.group_basic, label: labels.heading2, aliases: ["subtitulo", "h2", "##"],
      run: ({ editor, range }) => editor.chain().focus().deleteRange(range).setNode("heading", { level: 2 }).run() },
    { id: "h3", group: labels.group_basic, label: labels.heading3, aliases: ["h3", "###"],
      run: ({ editor, range }) => editor.chain().focus().deleteRange(range).setNode("heading", { level: 3 }).run() },
    { id: "bullet", group: labels.group_basic, label: labels.bullet_list, aliases: ["lista", "bullet", "ul", "-"],
      run: ({ editor, range }) => editor.chain().focus().deleteRange(range).toggleBulletList().run() },
    { id: "ordered", group: labels.group_basic, label: labels.ordered_list, aliases: ["numerada", "ordered", "ol", "1."],
      run: ({ editor, range }) => editor.chain().focus().deleteRange(range).toggleOrderedList().run() },
    { id: "quote", group: labels.group_basic, label: labels.quote, aliases: ["citacao", "quote", ">"],
      run: ({ editor, range }) => editor.chain().focus().deleteRange(range).toggleBlockquote().run() },
    { id: "divider", group: labels.group_basic, label: labels.divider, aliases: ["separador", "divider", "hr", "---"],
      run: ({ editor, range }) => editor.chain().focus().deleteRange(range).setHorizontalRule().run() },
  ];

  if (uploadImage) {
    list.push({
      id: "image", group: labels.group_media, label: labels.image,
      aliases: ["imagem", "img", "image", "foto"],
      run: ({ editor, range }) => {
        editor.chain().focus().deleteRange(range).run();
        pickImageFile((file) => insertImage(editor, file, uploadImage));
      },
    });
  }

  return list;
}

function filterCommands(commands, query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return commands;
  return commands.filter(
    (c) => c.label.toLowerCase().includes(q) || c.aliases.some((a) => a.includes(q)),
  );
}

function makeSlashMenu() {
  let el = null;
  let items = [];
  let active = 0;
  let onPick = () => {};

  const render = () => {
    if (!el) return;
    el.innerHTML = "";
    let lastGroup = null;
    items.forEach((item, index) => {
      if (item.group !== lastGroup) {
        const g = document.createElement("div");
        g.className = "gw-slash-group";
        g.textContent = item.group;
        el.appendChild(g);
        lastGroup = item.group;
      }
      const row = document.createElement("button");
      row.type = "button";
      row.className = "gw-slash-item" + (index === active ? " is-active" : "");
      row.textContent = item.label;
      row.addEventListener("mousedown", (e) => {
        e.preventDefault();
        onPick(item);
      });
      row.addEventListener("mousemove", () => {
        active = index;
        render();
      });
      el.appendChild(row);
    });
  };

  const position = (rect) => {
    if (!el || !rect) return;
    const margin = 6;
    el.style.left = `${Math.round(rect.left)}px`;
    const below = rect.bottom + margin;
    const wouldOverflow = below + el.offsetHeight > window.innerHeight;
    el.style.top = wouldOverflow
      ? `${Math.round(rect.top - el.offsetHeight - margin)}px`
      : `${Math.round(below)}px`;
  };

  return {
    open(nextItems, rect, pick) {
      onPick = pick;
      items = nextItems;
      active = 0;
      if (!el) {
        el = document.createElement("div");
        el.className = "gw-slash-menu";
        document.body.appendChild(el);
      }
      render();
      position(rect);
    },
    update(nextItems, rect) {
      items = nextItems;
      if (active >= items.length) active = Math.max(0, items.length - 1);
      render();
      position(rect);
    },
    move(delta) {
      if (!items.length) return;
      active = (active + delta + items.length) % items.length;
      render();
    },
    pick() {
      if (items[active]) onPick(items[active]);
    },
    isEmpty() {
      return items.length === 0;
    },
    close() {
      if (el) {
        el.remove();
        el = null;
      }
      items = [];
    },
  };
}

function slashExtension(commands, menu) {
  return Extension.create({
    name: "gwSlash",
    addProseMirrorPlugins() {
      return [
        Suggestion({
          editor: this.editor,
          char: "/",
          startOfLine: false,
          allowSpaces: false,
          command: ({ editor, range, props }) => props.run({ editor, range }),
          items: ({ query }) => filterCommands(commands, query),
          render: () => ({
            onStart: (props) => {
              menu.open(props.items, props.clientRect?.(), (item) => props.command(item));
            },
            onUpdate: (props) => {
              menu.update(props.items, props.clientRect?.());
            },
            onKeyDown: (props) => {
              const key = props.event.key;
              if (key === "Escape") {
                menu.close();
                return true;
              }
              if (menu.isEmpty()) return false;
              if (key === "ArrowDown") {
                menu.move(1);
                return true;
              }
              if (key === "ArrowUp") {
                menu.move(-1);
                return true;
              }
              if (key === "Enter" || key === "Tab") {
                menu.pick();
                return true;
              }
              return false;
            },
            onExit: () => menu.close(),
          }),
        }),
      ];
    },
  });
}


function mount(host, opts = {}) {
  const editable = opts.editable !== false;
  const labels = opts.labels || {};
  const isGm = !!opts.isGm;
  const uploadImage = editable ? opts.uploadImage : null;

  const extensions = [
    StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
    Link.configure({ openOnClick: !editable, autolink: true, HTMLAttributes: { rel: "noopener noreferrer", target: "_blank" } }),
    GwCallout,
    GwImage,
  ];
  let slashMenu = null;
  if (editable) {
    extensions.push(Placeholder.configure({ placeholder: labels.placeholder || "" }));
    slashMenu = makeSlashMenu();
    extensions.push(slashExtension(buildCommands(labels, uploadImage), slashMenu));
  }

  let editor;
  const handleFiles = (fileList) => {
    if (!uploadImage) return false;
    const files = Array.from(fileList || []).filter((f) => f.type && f.type.startsWith("image/"));
    if (!files.length) return false;
    files.forEach((file) => insertImage(editor, file, uploadImage));
    return true;
  };
  const editorProps = uploadImage
    ? {
        handlePaste: (_view, event) => handleFiles(event.clipboardData && event.clipboardData.files),
        handleDrop: (_view, event) => {
          const handled = handleFiles(event.dataTransfer && event.dataTransfer.files);
          if (handled) event.preventDefault();
          return handled;
        },
      }
    : undefined;

  editor = new Editor({
    element: host,
    editable,
    content: pmContentFrom(opts.doc),
    extensions,
    editorProps,
  });

  host.classList.add("gw-block-editor");
  if (!editable) host.classList.add("gw-block-editor--read");

  if (editable && typeof opts.onChange === "function") {
    editor.on("update", () => opts.onChange(wrapDoc(editor.getJSON())));
  }

  
  
  
  if (slashMenu) {
    editor.on("blur", () => slashMenu.close());
    editor.on("destroy", () => slashMenu.close());
  }

  return {
    editor,
    getDoc: () => wrapDoc(editor.getJSON()),
    setContent: (document) => editor.commands.setContent(pmContentFrom(document)),
    setContentFromHTML: (html) => editor.commands.setContent(html || ""),
    isEmpty: () => editor.isEmpty,
    focus: () => editor.commands.focus(),
    destroy: () => {
      slashMenu?.close();
      editor.destroy();
    },
  };
}

window.GWBlockEditor = { mount, DOC_FORMAT, DOC_VERSION };
document.dispatchEvent(new CustomEvent("gw:block-editor-ready"));
