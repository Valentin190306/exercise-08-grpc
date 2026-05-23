import sys
import os
import grpc
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Ensure the current directory is in the path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import node_registry_pb2
import node_registry_pb2_grpc

app = FastAPI(title="Node Registry REST Gateway")

# Configure the gRPC server address
GRPC_SERVER_ADDR = os.getenv("GRPC_SERVER_ADDR", "grpc-server:50051")

# Create gRPC channel and client stub
channel = grpc.insecure_channel(GRPC_SERVER_ADDR)
grpc_client = node_registry_pb2_grpc.NodeRegistryStub(channel)

class NodeCreate(BaseModel):
    name: str
    host: str
    port: int = Field(..., ge=1, le=65535)

def format_node_response(node):
    return {
        "id": node.id,
        "name": node.name,
        "host": node.host,
        "port": node.port,
        "status": node.status,
        "created_at": node.created_at,
        "updated_at": node.updated_at
    }

@app.get("/health")
def health_check():
    try:
        # Call Health RPC
        response = grpc_client.Health(node_registry_pb2.Empty())
        return {
            "status": response.status,
            "db": response.db,
            "nodes_count": response.nodes_count
        }
    except Exception as e:
        return {
            "status": "error",
            "db": "disconnected",
            "nodes_count": 0
        }

@app.post("/api/nodes", status_code=status.HTTP_201_CREATED)
def register_node(node: NodeCreate):
    try:
        response = grpc_client.Register(node_registry_pb2.RegisterRequest(
            name=node.name,
            host=node.host,
            port=node.port
        ))
        return format_node_response(response)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.ALREADY_EXISTS:
            raise HTTPException(status_code=409, detail="Node already exists")
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/nodes")
def list_nodes():
    try:
        response = grpc_client.List(node_registry_pb2.Empty())
        return [format_node_response(n) for n in response.nodes]
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=e.details())

@app.get("/api/nodes/{name}")
def get_node(name: str):
    try:
        response = grpc_client.Get(node_registry_pb2.GetRequest(name=name))
        return format_node_response(response)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Node not found")
        raise HTTPException(status_code=500, detail=e.details())

@app.delete("/api/nodes/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(name: str):
    try:
        grpc_client.Delete(node_registry_pb2.DeleteRequest(name=name))
        return None
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Node not found")
        raise HTTPException(status_code=500, detail=e.details())