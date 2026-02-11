# =============================================================================
# IndigoGlass Nexus - Graph Endpoints
# =============================================================================
"""
Neo4j-powered supply chain graph and impact analysis endpoints.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.security import TokenPayload, require_viewer
from app.db.neo4j import (
    run_query,
    get_impact_analysis,
    get_critical_path,
    get_data_lineage,
)

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class GraphNode(BaseModel):
    """Graph node representation."""
    id: str
    type: str
    name: str
    properties: dict = {}


class GraphEdge(BaseModel):
    """Graph edge representation."""
    source: str
    target: str
    relationship: str
    properties: dict = {}


class GraphResponse(BaseModel):
    """Graph query response."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int


class ImpactAnalysisResponse(BaseModel):
    """Impact analysis response."""
    source_node: GraphNode
    affected_nodes: list[GraphNode]
    impact_summary: dict


class LineageResponse(BaseModel):
    """Data lineage response."""
    entity: GraphNode
    lineage: list[GraphNode]
    depth: int


class PathResponse(BaseModel):
    """Critical path response."""
    product_id: str
    path: list[GraphNode]
    total_cost: float
    bottlenecks: list[str]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/network", response_model=GraphResponse)
async def get_supply_network(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    node_type: str | None = Query(None, description="Filter by node type"),
    region: str | None = Query(None, description="Filter by region"),
    limit: int = Query(100, ge=1, le=500),
) -> GraphResponse:
    """
    Get supply chain network graph for visualization.
    
    Returns nodes (suppliers, factories, warehouses, customers) and
    edges (supply relationships) for the selected filters.
    """
    # Build query based on filters
    where_clauses = []
    params = {"limit": limit}
    
    if node_type:
        where_clauses.append(f"n:{node_type}")
    if region:
        where_clauses.append("n.region = $region")
        params["region"] = region
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "true"
    
    query = f"""
    MATCH (n)
    WHERE {where_clause}
    WITH n LIMIT $limit
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN 
        n as source_node,
        type(r) as relationship,
        m as target_node
    """
    
    results = await run_query(query, params)
    
    nodes_map = {}
    edges = []
    
    for record in results:
        source = record.get("source_node")
        if source:
            node_id = source.get("id", str(source.id))
            if node_id not in nodes_map:
                nodes_map[node_id] = GraphNode(
                    id=node_id,
                    type=list(source.labels)[0] if hasattr(source, 'labels') else "Unknown",
                    name=source.get("name", node_id),
                    properties=dict(source),
                )
        
        target = record.get("target_node")
        rel = record.get("relationship")
        
        if target and rel:
            target_id = target.get("id", str(target.id))
            if target_id not in nodes_map:
                nodes_map[target_id] = GraphNode(
                    id=target_id,
                    type=list(target.labels)[0] if hasattr(target, 'labels') else "Unknown",
                    name=target.get("name", target_id),
                    properties=dict(target),
                )
            
            edges.append(GraphEdge(
                source=node_id,
                target=target_id,
                relationship=rel,
            ))
    
    return GraphResponse(
        nodes=list(nodes_map.values()),
        edges=edges,
        total_nodes=len(nodes_map),
        total_edges=len(edges),
    )


@router.get("/impact", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    node_type: str = Query(..., description="Node type (Warehouse, Supplier, Factory)"),
    node_id: str = Query(..., description="Node ID"),
    depth: int = Query(2, ge=1, le=5, description="Analysis depth (hops)"),
) -> ImpactAnalysisResponse:
    """
    Analyze supply chain impact if a node fails.
    
    Returns all downstream nodes that would be affected and
    a summary of the impact by node type.
    """
    # Get impact analysis
    results = await get_impact_analysis(node_type, node_id, depth)
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_type} with ID {node_id} not found",
        )
    
    source_node = GraphNode(
        id=node_id,
        type=node_type,
        name=node_id,
    )
    
    affected_nodes = []
    impact_by_type = {}
    
    for record in results:
        node_data = record.get("data", {})
        node_type_label = record.get("type", "Unknown")
        
        affected_nodes.append(GraphNode(
            id=node_data.get("id", ""),
            type=node_type_label,
            name=node_data.get("name", ""),
            properties=node_data,
        ))
        
        impact_by_type[node_type_label] = impact_by_type.get(node_type_label, 0) + 1
    
    return ImpactAnalysisResponse(
        source_node=source_node,
        affected_nodes=affected_nodes,
        impact_summary={
            "total_affected": len(affected_nodes),
            "by_type": impact_by_type,
            "max_depth": depth,
        },
    )


@router.get("/critical-path", response_model=PathResponse)
async def get_critical_supply_path(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    product_id: str = Query(..., description="Product ID to trace"),
) -> PathResponse:
    """
    Find the critical (longest/most constrained) path for a product.
    
    Traces from supplier to customer to identify bottlenecks.
    """
    results = await get_critical_path(product_id)
    
    path_nodes = []
    total_cost = 0.0
    bottlenecks = []
    
    if results:
        result = results[0]
        for node in result.get("nodes", []):
            path_nodes.append(GraphNode(
                id=node.get("id", ""),
                type=node.get("type", ""),
                name=node.get("id", ""),
            ))
        total_cost = result.get("total_cost", 0)
    
    return PathResponse(
        product_id=product_id,
        path=path_nodes,
        total_cost=total_cost,
        bottlenecks=bottlenecks,
    )


@router.get("/lineage", response_model=LineageResponse)
async def get_entity_lineage(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    entity_type: str = Query(..., description="Entity type"),
    entity_id: str = Query(..., description="Entity ID"),
) -> LineageResponse:
    """
    Trace data lineage for an entity.
    
    Shows which datasets and jobs produced the entity.
    """
    results = await get_data_lineage(entity_type, entity_id)
    
    entity = GraphNode(
        id=entity_id,
        type=entity_type,
        name=entity_id,
    )
    
    lineage_nodes = []
    max_depth = 0
    
    for record in results:
        for node in record.get("lineage", []):
            lineage_nodes.append(GraphNode(
                id=node.get("id", ""),
                type=node.get("type", ""),
                name=node.get("name", ""),
            ))
        max_depth = max(max_depth, record.get("depth", 0))
    
    return LineageResponse(
        entity=entity,
        lineage=lineage_nodes,
        depth=max_depth,
    )
