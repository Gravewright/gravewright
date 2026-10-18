"""The browser and server validate the same authored port combinations."""

from copy import deepcopy
import json
from pathlib import Path

from django.test import SimpleTestCase

from gravewright.maps.blueprints import NODE_TYPES, clean_blueprint, data_inputs, data_outputs, default_blueprint
from gravewright.maps.services import MapError


FIXTURE = json.loads((Path(__file__).resolve().parents[3] / "tests/fixtures/map_builder_connections.json").read_text(encoding="utf-8"))


def node(identifier, kind, fields):
    return {"id": identifier, "type": kind, "x": 20, "y": 20, **fields}


class ConnectionMatrixTests(SimpleTestCase):
    def test_fixture_covers_every_server_value_port(self):
        inputs, outputs = set(), set()
        for kind in NODE_TYPES:
            prototype = {"type": kind, "valueType": "boolean", "memberType": "element", "property": "userName"}
            inputs.update((kind, port) for port in data_inputs(prototype))
            outputs.update((kind, port) for port in data_outputs(prototype))
        self.assertEqual({(kind, port) for kind, port, *_ in FIXTURE["consumers"]}, inputs)
        self.assertEqual({(kind, port) for kind, port, *_ in FIXTURE["providers"]}, outputs)

    def test_every_producer_consumer_pair_agrees_with_the_shared_type_contract(self):
        resources = FIXTURE["resources"]
        for consumer, port, accepted, fields in FIXTURE["consumers"]:
            for producer, output, produced, configuration in FIXTURE["providers"]:
                with self.subTest(producer=producer, produced=produced, consumer=consumer, input=port, fields=fields):
                    blueprint = default_blueprint("lever")
                    graph = {"nodes": [node("event", "event", {"event": "interact"}),
                        node("producer", producer, configuration), node("consumer", consumer, fields)],
                        "edges": [{"from": "producer", "output": output, "to": "consumer", "input": port, "kind": "data"}]}
                    blueprint["graphs"]["interact"] = graph
                    before = deepcopy(blueprint)
                    if produced in accepted:
                        cleaned = clean_blueprint(blueprint,
                            asset_ids={entry["id"] for entry in resources["assets"]},
                            light_ids={entry["id"] for entry in resources["lights"]},
                            track_ids={entry["id"] for entry in resources["sounds"]})
                        self.assertEqual(cleaned["graphs"]["interact"]["edges"], graph["edges"])
                        duplicate = deepcopy(blueprint)
                        duplicate["graphs"]["interact"]["edges"].append(deepcopy(graph["edges"][0]))
                        with self.assertRaisesMessage(MapError, "one blueprint connection per input"):
                            clean_blueprint(duplicate)
                    else:
                        with self.assertRaisesMessage(MapError, "connection"):
                            clean_blueprint(blueprint)
                    self.assertEqual(blueprint, before, "Validation must not rewrite a draft on success or failure.")

    def test_targetless_nodes_never_accept_a_value_reference(self):
        for consumer, fields in (("event", {"event": "interact"}),
                                 ("showMessage", {"text": "Message", "audience": {"scope": "trigger"}})):
            for producer, output, produced, configuration in FIXTURE["providers"]:
                with self.subTest(producer=producer, produced=produced, consumer=consumer):
                    blueprint = default_blueprint("lever")
                    blueprint["graphs"]["interact"] = {
                        "nodes": ([] if consumer == "event" else [node("event", "event", {"event": "interact"})])
                                 + [node("producer", producer, configuration), node("consumer", consumer, fields)],
                        "edges": [{"from": "producer", "output": output, "to": "consumer", "input": "target", "kind": "data"}]}
                    before = deepcopy(blueprint)
                    with self.assertRaisesMessage(MapError, "Invalid blueprint connection input"):
                        clean_blueprint(blueprint)
                    self.assertEqual(blueprint, before)
