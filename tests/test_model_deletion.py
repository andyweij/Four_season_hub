import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from app.modules.llm_management.catalog_loader import load_catalog_file
from app.modules.llm_management.repositories.memory_model_catalog import InMemoryModelCatalog
from app.modules.llm_management.services.model_registry_service import ModelRegistryService
from app.modules.cloud_llm_management.services.cloud_llm_mgt_service import CloudLLMManagementService

ROOT = Path(__file__).resolve().parents[1]

class ModelDeletionTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_removal_persists_and_preserves_other_entries_and_artifact(self):
        raw = json.loads((ROOT / "resources/models/models.json").read_text(encoding="utf-8"))
        name = next(iter(raw))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "models.json"
            artifact = Path(directory) / "model.gguf"
            artifact.write_bytes(b"preserve-model")
            path.write_text(json.dumps(raw), encoding="utf-8")
            catalog = InMemoryModelCatalog(load_catalog_file(path), catalog_path=path)
            self.assertTrue(await catalog.remove(name))
            self.assertFalse(await catalog.remove(name))
            remaining = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn(name, remaining)
            self.assertEqual(remaining, {key: value for key, value in raw.items() if key != name})
            self.assertEqual(artifact.read_bytes(), b"preserve-model")
            self.assertNotIn(name, [item.model_name for item in load_catalog_file(path)])

    async def test_running_local_model_cannot_be_removed(self):
        registry = ModelRegistryService(None, None, None, "localhost", "", "vllm", None)
        registry._model_catalog = SimpleNamespace(remove=AsyncMock())
        registry._registry["running"] = SimpleNamespace(instance=object())
        with self.assertRaises(ValueError):
            await registry.remove_registration("running")
        registry._model_catalog.remove.assert_not_awaited()

    async def test_local_removal_updates_registry(self):
        catalog = SimpleNamespace(remove=AsyncMock(return_value=True))
        registry = ModelRegistryService(catalog, None, None, "localhost", "", "vllm", None)
        registry._registry["idle"] = SimpleNamespace(instance=None)
        await registry.remove_registration("idle")
        self.assertIsNone(registry.get("idle"))
        catalog.remove.assert_awaited_once_with("idle")

    async def test_cloud_deletion_missing_and_success(self):
        repository = SimpleNamespace(delete=AsyncMock(return_value=True))
        service = CloudLLMManagementService(repository, None)
        await service.delete("conn_test")
        repository.delete.assert_awaited_once_with("conn_test")
        repository.delete.return_value = False
        with self.assertRaises(LookupError):
            await service.delete("missing")
