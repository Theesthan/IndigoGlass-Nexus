# =============================================================================
# IndigoGlass Nexus - Neo4j Connection
# =============================================================================
"""
Neo4j graph database connection for supply chain network.
"""

from typing import Any, Dict, List, Optional

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.core.config import settings

logger = structlog.get_logger()

# Global driver
_driver: Optional[AsyncDriver] = None


async def init_neo4j() -> None:
    """Initialize Neo4j connection."""
    global _driver
    
    _driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        max_connection_pool_size=50,
    )
    
    # Verify connectivity
    await _driver.verify_connectivity()
    
    # Create constraints and indexes
    await _create_constraints()
    
    logger.info("neo4j_initialized", uri=settings.NEO4J_URI)


async def _create_constraints() -> None:
    """Create required constraints and indexes in Neo4j."""
    if not _driver:
        return
    
    async with _driver.session() as session:
        constraints = [
            "CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (s:Supplier) REQUIRE s.supplier_id IS UNIQUE",
            "CREATE CONSTRAINT factory_id IF NOT EXISTS FOR (f:Factory) REQUIRE f.factory_id IS UNIQUE",
            "CREATE CONSTRAINT warehouse_id IF NOT EXISTS FOR (w:Warehouse) REQUIRE w.warehouse_id IS UNIQUE",
            "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE",
            "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
            "CREATE CONSTRAINT batch_job_id IF NOT EXISTS FOR (b:BatchJob) REQUIRE b.job_id IS UNIQUE",
            "CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (d:Dataset) REQUIRE d.dataset_id IS UNIQUE",
        ]
        
        for constraint in constraints:
            try:
                await session.run(constraint)
            except Exception as e:
                # Ignore if constraint exists
                if "already exists" not in str(e).lower():
                    logger.warning("neo4j_constraint_error", constraint=constraint, error=str(e))
    
    logger.info("neo4j_constraints_created")


async def close_neo4j() -> None:
    """Close Neo4j connection."""
    global _driver
    
    if _driver:
        await _driver.close()
        _driver = None
        logger.info("neo4j_closed")


def get_driver() -> AsyncDriver:
    """Get the Neo4j driver."""
    if not _driver:
        raise RuntimeError("Neo4j not initialized. Call init_neo4j() first.")
    return _driver


async def run_query(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    database: str = "neo4j",
) -> List[Dict[str, Any]]:
    """Run a Cypher query and return results as a list of dicts."""
    driver = get_driver()
    
    async with driver.session(database=database) as session:
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records


async def run_write_query(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    database: str = "neo4j",
) -> Dict[str, Any]:
    """Run a write Cypher query and return summary."""
    driver = get_driver()
    
    async with driver.session(database=database) as session:
        result = await session.run(query, parameters or {})
        summary = await result.consume()
        return {
            "nodes_created": summary.counters.nodes_created,
            "nodes_deleted": summary.counters.nodes_deleted,
            "relationships_created": summary.counters.relationships_created,
            "relationships_deleted": summary.counters.relationships_deleted,
            "properties_set": summary.counters.properties_set,
        }


async def check_neo4j_health() -> bool:
    """Check if Neo4j is healthy."""
    try:
        if not _driver:
            return False
        await _driver.verify_connectivity()
        return True
    except Exception as e:
        logger.warning("neo4j_health_check_failed", error=str(e))
        return False


# =============================================================================
# Supply Chain Graph Operations
# =============================================================================

async def get_impact_analysis(
    node_type: str,
    node_id: str,
    depth: int = 2,
) -> List[Dict[str, Any]]:
    """
    Analyze impact of a node failure on the supply chain.
    Returns affected nodes within specified hop depth.
    """
    query = """
    MATCH (n {%s_id: $node_id})
    CALL apoc.path.subgraphNodes(n, {
        maxLevel: $depth,
        relationshipFilter: "SUPPLIES_TO>|SHIPS_TO>|DELIVERS>"
    }) YIELD node
    RETURN 
        labels(node)[0] as type,
        node as data,
        apoc.path.shortestPath(n, node, "SUPPLIES_TO|SHIPS_TO|DELIVERS") as path_length
    ORDER BY path_length
    """ % node_type.lower()
    
    return await run_query(query, {"node_id": node_id, "depth": depth})


async def get_critical_path(
    product_id: str,
    from_type: str = "Supplier",
    to_type: str = "Customer",
) -> List[Dict[str, Any]]:
    """
    Find the critical (longest) path for a product from supplier to customer.
    """
    query = """
    MATCH path = (s:%s)-[:SUPPLIES_TO|SHIPS_TO|DELIVERS*]->(c:%s)
    WHERE EXISTS { (p:Product {product_id: $product_id})-[:PRODUCES|STORES]-() }
    RETURN 
        [n in nodes(path) | {type: labels(n)[0], id: n.id}] as nodes,
        length(path) as path_length,
        reduce(cost = 0, r in relationships(path) | cost + coalesce(r.cost, 0)) as total_cost
    ORDER BY path_length DESC
    LIMIT 1
    """ % (from_type, to_type)
    
    return await run_query(query, {"product_id": product_id})


async def get_data_lineage(
    entity_type: str,
    entity_id: str,
) -> List[Dict[str, Any]]:
    """
    Trace data lineage - which dataset/job produced an entity.
    """
    query = """
    MATCH path = (e {id: $entity_id})<-[:GENERATED_BY*]-(source)
    RETURN 
        [n in nodes(path) | {type: labels(n)[0], id: n.id, name: n.name}] as lineage,
        length(path) as depth
    ORDER BY depth DESC
    LIMIT 10
    """
    
    return await run_query(query, {"entity_id": entity_id})
