#!/usr/bin/env python3
"""
IndigoGlass Nexus - Synthetic Data Generator
Generates realistic supply chain data for development and testing.
"""

import random
import string
from datetime import datetime, timedelta
from pathlib import Path
import json
import csv
import argparse
from typing import Generator
import hashlib

# Configuration
PRODUCTS = [
    ("Paracetamol 500mg", "Pharma", 12.50),
    ("Ibuprofen 200mg", "Pharma", 8.75),
    ("Vitamin C 1000mg", "Pharma", 15.00),
    ("Aspirin 100mg", "Pharma", 6.50),
    ("Omeprazole 20mg", "Pharma", 22.00),
    ("Metformin 500mg", "Pharma", 18.50),
    ("Atorvastatin 10mg", "Pharma", 28.00),
    ("Lisinopril 5mg", "Pharma", 14.00),
    ("Hand Sanitizer 500ml", "Consumer", 5.50),
    ("Face Mask N95 (10pk)", "Consumer", 25.00),
    ("First Aid Kit", "Medical", 45.00),
    ("Blood Pressure Monitor", "Medical", 89.00),
    ("Digital Thermometer", "Medical", 12.00),
    ("Pulse Oximeter", "Medical", 35.00),
    ("Bandages (100pk)", "Medical", 8.00),
]

LOCATIONS = [
    ("WH-A", "Warehouse A", "warehouse", 40.7128, -74.0060),  # NYC
    ("WH-B", "Warehouse B", "warehouse", 34.0522, -118.2437),  # LA
    ("DC-N", "DC North", "dc", 41.8781, -87.6298),  # Chicago
    ("DC-S", "DC South", "dc", 29.7604, -95.3698),  # Houston
    ("DC-E", "DC East", "dc", 33.7490, -84.3880),  # Atlanta
    ("DC-W", "DC West", "dc", 47.6062, -122.3321),  # Seattle
]

CARRIERS = [
    ("CAR-001", "FastFreight", 0.85, 1.2),  # reliability, cost_per_km
    ("CAR-002", "ExpressLogistics", 0.92, 1.5),
    ("CAR-003", "EcoTransport", 0.88, 0.9),
    ("CAR-004", "PrimeShipping", 0.95, 1.8),
]

SUPPLIERS = [
    ("SUP-001", "PharmaChem Ltd", "supplier", 1),
    ("SUP-002", "BioActive Inc", "supplier", 1),
    ("SUP-003", "MedSupply Co", "supplier", 2),
]


def generate_sku() -> str:
    """Generate a unique SKU."""
    return f"SKU-{random.randint(10000, 99999)}"


def generate_sales_data(
    start_date: datetime,
    end_date: datetime,
    products: list,
    locations: list,
) -> Generator[dict, None, None]:
    """Generate daily sales transactions."""
    current = start_date
    while current <= end_date:
        for product in products:
            for location in locations:
                if location[2] not in ["dc", "warehouse"]:
                    continue
                    
                # Base demand with seasonality
                day_of_year = current.timetuple().tm_yday
                seasonality = 1 + 0.3 * (1 + random.gauss(0, 0.1)) * (
                    0.5 + 0.5 * abs((day_of_year - 180) / 180)
                )
                
                # Weekend effect
                day_of_week = current.weekday()
                weekend_effect = 0.7 if day_of_week >= 5 else 1.0
                
                # Random demand
                base_demand = random.randint(50, 500)
                quantity = int(base_demand * seasonality * weekend_effect)
                
                if quantity > 0:
                    yield {
                        "transaction_id": hashlib.md5(
                            f"{current.isoformat()}-{product[0]}-{location[0]}".encode()
                        ).hexdigest()[:16],
                        "date": current.strftime("%Y-%m-%d"),
                        "product_name": product[0],
                        "category": product[1],
                        "sku": generate_sku(),
                        "location_code": location[0],
                        "location_name": location[1],
                        "quantity": quantity,
                        "unit_price": product[2],
                        "total_amount": round(quantity * product[2], 2),
                        "channel": random.choice(["retail", "wholesale", "online"]),
                    }
        current += timedelta(days=1)


def generate_inventory_snapshots(
    start_date: datetime,
    end_date: datetime,
    products: list,
    locations: list,
) -> Generator[dict, None, None]:
    """Generate daily inventory snapshots."""
    # Initialize inventory levels
    inventory = {}
    for product in products:
        for location in locations:
            key = (product[0], location[0])
            inventory[key] = random.randint(5000, 20000)
    
    current = start_date
    while current <= end_date:
        for product in products:
            for location in locations:
                key = (product[0], location[0])
                
                # Simulate inventory changes
                sold = random.randint(50, 300)
                received = random.randint(0, 400) if random.random() > 0.7 else 0
                
                inventory[key] = max(0, inventory[key] - sold + received)
                
                # Calculate safety stock and reorder point
                safety_stock = random.randint(500, 2000)
                reorder_point = safety_stock * 2
                
                yield {
                    "snapshot_id": hashlib.md5(
                        f"{current.isoformat()}-{product[0]}-{location[0]}".encode()
                    ).hexdigest()[:16],
                    "date": current.strftime("%Y-%m-%d"),
                    "product_name": product[0],
                    "category": product[1],
                    "location_code": location[0],
                    "location_name": location[1],
                    "quantity_on_hand": inventory[key],
                    "quantity_reserved": random.randint(0, inventory[key] // 10),
                    "quantity_available": inventory[key],
                    "safety_stock": safety_stock,
                    "reorder_point": reorder_point,
                    "avg_daily_demand": random.randint(100, 300),
                    "days_of_supply": round(inventory[key] / random.randint(100, 300), 1),
                }
        current += timedelta(days=1)


def generate_shipments(
    start_date: datetime,
    end_date: datetime,
    locations: list,
    carriers: list,
) -> Generator[dict, None, None]:
    """Generate shipment records."""
    current = start_date
    shipment_id = 1000
    
    while current <= end_date:
        num_shipments = random.randint(5, 20)
        
        for _ in range(num_shipments):
            origin = random.choice(locations)
            destination = random.choice([l for l in locations if l[0] != origin[0]])
            carrier = random.choice(carriers)
            
            # Calculate distance (simplified)
            distance = ((origin[3] - destination[3])**2 + (origin[4] - destination[4])**2)**0.5 * 111
            
            # Delivery time based on distance
            transit_days = max(1, int(distance / 500))
            
            # Actual delivery (with potential delays)
            if random.random() > carrier[2]:
                actual_days = transit_days + random.randint(1, 3)
            else:
                actual_days = transit_days
            
            ship_date = current + timedelta(hours=random.randint(0, 12))
            expected_delivery = ship_date + timedelta(days=transit_days)
            actual_delivery = ship_date + timedelta(days=actual_days)
            
            yield {
                "shipment_id": f"SHP-{shipment_id}",
                "ship_date": ship_date.strftime("%Y-%m-%d %H:%M:%S"),
                "expected_delivery": expected_delivery.strftime("%Y-%m-%d"),
                "actual_delivery": actual_delivery.strftime("%Y-%m-%d") if actual_delivery <= datetime.now() else None,
                "origin_code": origin[0],
                "origin_name": origin[1],
                "destination_code": destination[0],
                "destination_name": destination[1],
                "carrier_code": carrier[0],
                "carrier_name": carrier[1],
                "distance_km": round(distance, 1),
                "weight_kg": random.randint(100, 5000),
                "num_pallets": random.randint(1, 20),
                "cost": round(distance * carrier[3], 2),
                "co2_kg": round(distance * 0.1 * carrier[3], 2),
                "status": "delivered" if actual_delivery <= datetime.now() else "in_transit",
                "on_time": actual_days <= transit_days,
            }
            
            shipment_id += 1
        
        current += timedelta(days=1)


def generate_supply_chain_graph(
    suppliers: list,
    locations: list,
) -> dict:
    """Generate Neo4j-compatible graph data."""
    nodes = []
    edges = []
    
    # Add supplier nodes
    for sup in suppliers:
        nodes.append({
            "id": sup[0],
            "name": sup[1],
            "type": sup[2],
            "tier": sup[3],
        })
    
    # Add location nodes
    for loc in locations:
        nodes.append({
            "id": loc[0],
            "name": loc[1],
            "type": loc[2],
            "lat": loc[3],
            "lon": loc[4],
        })
    
    # Create edges
    # Tier 2 -> Tier 1
    edges.append({
        "source": "SUP-003",
        "target": "SUP-001",
        "relationship": "SUPPLIES",
        "lead_time_days": 14,
        "reliability": 0.92,
    })
    
    # Tier 1 -> Factories (using warehouses as pseudo-factories)
    for sup in suppliers:
        if sup[3] == 1:
            target = random.choice([l for l in locations if l[2] == "warehouse"])
            edges.append({
                "source": sup[0],
                "target": target[0],
                "relationship": "SUPPLIES",
                "lead_time_days": random.randint(3, 7),
                "reliability": random.uniform(0.85, 0.98),
            })
    
    # Warehouses -> DCs
    for wh in [l for l in locations if l[2] == "warehouse"]:
        for dc in [l for l in locations if l[2] == "dc"]:
            edges.append({
                "source": wh[0],
                "target": dc[0],
                "relationship": "SHIPS_TO",
                "lead_time_days": random.randint(1, 4),
                "reliability": random.uniform(0.90, 0.99),
            })
    
    return {"nodes": nodes, "edges": edges}


def save_csv(data: list, filepath: Path, fieldnames: list = None):
    """Save data to CSV file."""
    if not data:
        return
    
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Saved {len(data)} records to {filepath}")


def save_json(data: dict | list, filepath: Path):
    """Save data to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic supply chain data")
    parser.add_argument("--days", type=int, default=90, help="Number of days of data")
    parser.add_argument("--output", type=str, default="./data/synthetic", help="Output directory")
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    print(f"Generating {args.days} days of synthetic data...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Generate sales data
    print("Generating sales data...")
    sales = list(generate_sales_data(start_date, end_date, PRODUCTS, LOCATIONS))
    save_csv(sales, output_dir / "sales.csv")
    
    # Generate inventory snapshots
    print("Generating inventory snapshots...")
    inventory = list(generate_inventory_snapshots(start_date, end_date, PRODUCTS, LOCATIONS))
    save_csv(inventory, output_dir / "inventory.csv")
    
    # Generate shipments
    print("Generating shipment records...")
    shipments = list(generate_shipments(start_date, end_date, LOCATIONS, CARRIERS))
    save_csv(shipments, output_dir / "shipments.csv")
    
    # Generate supply chain graph
    print("Generating supply chain graph...")
    graph = generate_supply_chain_graph(SUPPLIERS, LOCATIONS)
    save_json(graph, output_dir / "supply_chain_graph.json")
    
    # Generate dimension tables
    print("Generating dimension tables...")
    
    # Products dimension
    products_dim = [
        {
            "sku": f"SKU-{i:05d}",
            "name": p[0],
            "category": p[1],
            "unit_price": p[2],
            "weight_kg": round(random.uniform(0.1, 5.0), 2),
            "volume_m3": round(random.uniform(0.001, 0.05), 4),
        }
        for i, p in enumerate(PRODUCTS, start=10001)
    ]
    save_csv(products_dim, output_dir / "dim_products.csv")
    
    # Locations dimension
    locations_dim = [
        {
            "code": l[0],
            "name": l[1],
            "type": l[2],
            "latitude": l[3],
            "longitude": l[4],
            "capacity_units": random.randint(50000, 200000),
            "cost_per_unit": round(random.uniform(0.5, 2.0), 2),
        }
        for l in LOCATIONS
    ]
    save_csv(locations_dim, output_dir / "dim_locations.csv")
    
    # Carriers dimension
    carriers_dim = [
        {
            "code": c[0],
            "name": c[1],
            "reliability": c[2],
            "cost_per_km": c[3],
            "avg_speed_kmh": random.randint(60, 100),
            "co2_per_km": round(random.uniform(0.08, 0.15), 3),
        }
        for c in CARRIERS
    ]
    save_csv(carriers_dim, output_dir / "dim_carriers.csv")
    
    print()
    print("Data generation complete!")
    print(f"Total records generated:")
    print(f"  - Sales: {len(sales):,}")
    print(f"  - Inventory: {len(inventory):,}")
    print(f"  - Shipments: {len(shipments):,}")
    print(f"  - Graph nodes: {len(graph['nodes'])}")
    print(f"  - Graph edges: {len(graph['edges'])}")


if __name__ == "__main__":
    main()
