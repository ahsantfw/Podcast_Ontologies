"""
Graph Exploration Endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Header
from typing import Optional, List
from pydantic import BaseModel
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core_engine.kg.neo4j_client import get_neo4j_client
from core_engine.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/graph/stats")
async def get_graph_stats(x_workspace_id: Optional[str] = Header(None)):
    """Get Knowledge Graph statistics for workspace."""
    workspace_id = x_workspace_id or "default"
    
    try:
        client = get_neo4j_client(workspace_id=workspace_id)
        
        # Total nodes
        query = """
        MATCH (n)
        WHERE n.workspace_id = $workspace_id
        RETURN count(n) as total
        """
        result = client.execute_read(query, {"workspace_id": workspace_id})
        total_nodes = result[0]["total"] if result else 0
        
        # Total relationships
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
        RETURN count(r) as total
        """
        result = client.execute_read(query, {"workspace_id": workspace_id})
        total_rels = result[0]["total"] if result else 0
        
        # Nodes by type
        query = """
        MATCH (n)
        WHERE n.workspace_id = $workspace_id
        RETURN labels(n)[0] as type, count(*) as count
        ORDER BY count DESC
        """
        result = client.execute_read(query, {"workspace_id": workspace_id})
        by_type = {r["type"]: r["count"] for r in result}
        
        # Relationships by type
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.workspace_id = $workspace_id AND b.workspace_id = $workspace_id
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 10
        """
        result = client.execute_read(query, {"workspace_id": workspace_id})
        by_rel_type = {r["rel_type"]: r["count"] for r in result}
        
        client.close()
        
        return {
            "workspace_id": workspace_id,
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "by_type": by_type,
            "relationships_by_type": by_rel_type
        }
    except Exception as e:
        logger.error("get_stats_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/graph/concepts")
async def get_concepts(
    theme: Optional[str] = Query(None),
    concept_type: Optional[str] = Query(None),
    x_workspace_id: Optional[str] = Header(None),
    limit: int = 50
):
    """List concepts in workspace, optionally filtered by theme/type."""
    workspace_id = x_workspace_id or "default"
    
    try:
        client = get_neo4j_client(workspace_id=workspace_id)
        
        query = """
        MATCH (c)
        WHERE c.workspace_id = $workspace_id
        """
        
        params = {"workspace_id": workspace_id, "limit": limit}
        
        if theme:
            query += """
              AND (
                toLower(c.name) CONTAINS toLower($theme)
                OR toLower(c.description) CONTAINS toLower($theme)
              )
            """
            params["theme"] = theme
        
        if concept_type:
            query += """
              AND labels(c)[0] = $concept_type
            """
            params["concept_type"] = concept_type
        
        query += """
        RETURN c.id as id,
               c.name as name,
               labels(c)[0] as type,
               c.description as description,
               c.episode_ids as episode_ids
        ORDER BY c.name
        LIMIT $limit
        """
        
        result = client.execute_read(query, params)
        client.close()
        
        return [dict(r) for r in result]
        
    except Exception as e:
        logger.error("get_concepts_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get concepts: {str(e)}")

@router.get("/graph/concepts/{concept_id}")
async def get_concept_detail(concept_id: str, x_workspace_id: Optional[str] = Header(None)):
    """Get concept details with relationships."""
    workspace_id = x_workspace_id or "default"
    
    try:
        client = get_neo4j_client(workspace_id=workspace_id)
        
        # Get concept
        query = """
        MATCH (c)
        WHERE c.id = $concept_id AND c.workspace_id = $workspace_id
        RETURN c.id as id,
               c.name as name,
               labels(c)[0] as type,
               c.description as description,
               c.episode_ids as episode_ids,
               c.source_paths as source_paths
        LIMIT 1
        """
        result = client.execute_read(query, {"concept_id": concept_id, "workspace_id": workspace_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="Concept not found")
        
        concept = dict(result[0])
        
        # Get relationships
        query = """
        MATCH (c)-[r]->(target)
        WHERE c.id = $concept_id 
          AND c.workspace_id = $workspace_id
          AND target.workspace_id = $workspace_id
        RETURN type(r) as relationship_type,
               target.id as target_id,
               target.name as target_name,
               labels(target)[0] as target_type,
               r.description as description
        LIMIT 20
        """
        result = client.execute_read(query, {"concept_id": concept_id, "workspace_id": workspace_id})
        
        concept["relationships"] = [dict(r) for r in result]
        
        client.close()
        
        return concept
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_concept_failed", exc_info=True, extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get concept: {str(e)}")

