"""
Project management API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os
from indexer.vector_store import VectorStore

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectInfo(BaseModel):
    name: str
    collection_name: str
    total_chunks: int


@router.get("/", response_model=List[ProjectInfo])
async def list_projects():
    """
    List all available projects/collections

    Example:
        GET /api/projects/
        Returns: [{"name": "privy", "collection_name": "privy", "total_chunks": 1250}, ...]
    """
    try:
        # For now, return known projects. In production, you might scan the DB
        # or maintain a registry of projects
        projects = ["polymarket", "privy"]  # Available documentation projects

        project_info = []
        for project in projects:
            collection_name = project.lower().replace(' ', '_')
            try:
                store = VectorStore(collection_name=collection_name)
                stats = store.get_stats()
                project_info.append({
                    "name": project,
                    "collection_name": collection_name,
                    "total_chunks": stats["total_chunks"]
                })
            except Exception as e:
                # Collection doesn't exist yet or error accessing it
                project_info.append({
                    "name": project,
                    "collection_name": collection_name,
                    "total_chunks": 0
                })

        return project_info

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing projects: {str(e)}")


@router.delete("/{project_name}")
async def delete_project(project_name: str):
    """
    Delete a project collection

    Example:
        DELETE /api/projects/privy
        Returns: {"message": "Project 'privy' deleted"}
    """
    try:
        collection_name = project_name.lower().replace(' ', '_')
        store = VectorStore(collection_name=collection_name)
        store.clear_collection()
        return {"message": f"Project '{project_name}' deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting project: {str(e)}")
