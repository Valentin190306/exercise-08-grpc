import requests
import uuid

BASE_URL = "http://localhost:8080"

# Generate a unique name for the test run to avoid soft-delete collisions
unique_suffix = uuid.uuid4().hex[:8]
NODE_NAME = f"node-test-{unique_suffix}"

def test_health_check_initial():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert isinstance(data["nodes_count"], int)

def test_register_node_success():
    payload = {
        "name": NODE_NAME,
        "host": "192.168.1.200",
        "port": 8888
    }
    response = requests.post(f"{BASE_URL}/api/nodes", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["host"] == payload["host"]
    assert data["port"] == payload["port"]
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_register_node_duplicate():
    payload = {
        "name": NODE_NAME,
        "host": "192.168.1.200",
        "port": 8888
    }
    # Second registration of the same name should fail with 409
    response = requests.post(f"{BASE_URL}/api/nodes", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "Node already exists"

def test_get_node_success():
    response = requests.get(f"{BASE_URL}/api/nodes/{NODE_NAME}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == NODE_NAME
    assert data["host"] == "192.168.1.200"
    assert data["port"] == 8888
    assert data["status"] == "active"

def test_get_node_not_found():
    response = requests.get(f"{BASE_URL}/api/nodes/this-node-does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Node not found"

def test_list_nodes():
    response = requests.get(f"{BASE_URL}/api/nodes")
    assert response.status_code == 200
    nodes = response.json()
    assert isinstance(nodes, list)
    names = [node["name"] for node in nodes]
    assert NODE_NAME in names

def test_delete_node_success():
    response = requests.delete(f"{BASE_URL}/api/nodes/{NODE_NAME}")
    assert response.status_code == 204

    # Verify status is now "inactive" when fetching it
    response = requests.get(f"{BASE_URL}/api/nodes/{NODE_NAME}")
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"

def test_delete_node_not_found():
    response = requests.delete(f"{BASE_URL}/api/nodes/this-node-does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Node not found"
