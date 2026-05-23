import sys
import os
from concurrent import futures
import time
import grpc

# Ensure the current directory is in the path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import node_registry_pb2
import node_registry_pb2_grpc
import models
from database import SessionLocal, engine, Base

# Auto-create database tables
Base.metadata.create_all(bind=engine)

class NodeRegistryServicer(node_registry_pb2_grpc.NodeRegistryServicer):
    def Register(self, request, context):
        db = SessionLocal()
        try:
            db_node = db.query(models.Node).filter(models.Node.name == request.name).first()
        except Exception as e:
            db.close()
            context.abort(grpc.StatusCode.INTERNAL, f"Database error during lookup: {str(e)}")

        if db_node:
            db.close()
            context.abort(grpc.StatusCode.ALREADY_EXISTS, "Node already exists")

        try:
            new_node = models.Node(
                name=request.name,
                host=request.host,
                port=request.port
            )
            db.add(new_node)
            db.commit()
            db.refresh(new_node)
            
            response = node_registry_pb2.NodeResponse(
                id=new_node.id,
                name=new_node.name,
                host=new_node.host,
                port=new_node.port,
                status=new_node.status,
                created_at=new_node.created_at.isoformat() if new_node.created_at else "",
                updated_at=new_node.updated_at.isoformat() if new_node.updated_at else ""
            )
            db.close()
            return response
        except Exception as e:
            db.close()
            context.abort(grpc.StatusCode.INTERNAL, f"Database error during creation: {str(e)}")

    def List(self, request, context):
        db = SessionLocal()
        try:
            nodes = db.query(models.Node).all()
            proto_nodes = []
            for node in nodes:
                proto_nodes.append(node_registry_pb2.NodeResponse(
                    id=node.id,
                    name=node.name,
                    host=node.host,
                    port=node.port,
                    status=node.status,
                    created_at=node.created_at.isoformat() if node.created_at else "",
                    updated_at=node.updated_at.isoformat() if node.updated_at else ""
                ))
            db.close()
            return node_registry_pb2.NodeList(nodes=proto_nodes)
        except Exception as e:
            db.close()
            context.abort(grpc.StatusCode.INTERNAL, f"Database error during list: {str(e)}")

    def Get(self, request, context):
        db = SessionLocal()
        try:
            node = db.query(models.Node).filter(models.Node.name == request.name).first()
        except Exception as e:
            db.close()
            context.abort(grpc.StatusCode.INTERNAL, f"Database error during lookup: {str(e)}")

        if not node:
            db.close()
            context.abort(grpc.StatusCode.NOT_FOUND, "Node not found")

        response = node_registry_pb2.NodeResponse(
            id=node.id,
            name=node.name,
            host=node.host,
            port=node.port,
            status=node.status,
            created_at=node.created_at.isoformat() if node.created_at else "",
            updated_at=node.updated_at.isoformat() if node.updated_at else ""
        )
        db.close()
        return response

    def Delete(self, request, context):
        db = SessionLocal()
        try:
            node = db.query(models.Node).filter(models.Node.name == request.name).first()
        except Exception as e:
            db.close()
            context.abort(grpc.StatusCode.INTERNAL, f"Database error during lookup: {str(e)}")

        if not node:
            db.close()
            context.abort(grpc.StatusCode.NOT_FOUND, "Node not found")

        try:
            node.status = "inactive"
            db.commit()
            db.close()
            return node_registry_pb2.Empty()
        except Exception as e:
            db.close()
            context.abort(grpc.StatusCode.INTERNAL, f"Database error during delete: {str(e)}")

    def Health(self, request, context):
        db = SessionLocal()
        db_status = "disconnected"
        active_count = 0
        try:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            db_status = "connected"
            active_count = db.query(models.Node).filter(models.Node.status == "active").count()
        except Exception:
            db_status = "disconnected"
        finally:
            db.close()
        
        return node_registry_pb2.HealthResponse(
            status="ok",
            db=db_status,
            nodes_count=active_count
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    node_registry_pb2_grpc.add_NodeRegistryServicer_to_server(NodeRegistryServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server running on [::]:50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    serve()