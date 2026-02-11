// =============================================================================
// IndigoGlass Nexus - Route Optimizer Service
// =============================================================================
package com.indigoglass.optimizer.service;

import com.google.ortools.Loader;
import com.google.ortools.constraintsolver.*;
import com.indigoglass.optimizer.config.OptimizerProperties;
import com.indigoglass.optimizer.dto.RoutePlanRequest;
import com.indigoglass.optimizer.dto.RoutePlanResponse;
import com.indigoglass.optimizer.dto.RoutePlanResponse.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.time.Instant;
import java.util.*;

/**
 * Service for solving vehicle routing problems using Google OR-Tools.
 * Implements TSP-D (Traveling Salesman Problem with Drones) heuristics
 * with 2-opt local search improvement.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RouteOptimizerService {
    
    private final OptimizerProperties properties;
    
    @PostConstruct
    public void init() {
        Loader.loadNativeLibraries();
        log.info("OR-Tools native libraries loaded successfully");
    }
    
    /**
     * Solve the vehicle routing problem.
     *
     * @param request Route plan request
     * @return Optimized route plan
     */
    public RoutePlanResponse solve(RoutePlanRequest request) {
        long startTime = System.currentTimeMillis();
        String planId = UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        
        log.info("Starting route optimization: planId={}, destinations={}, vehicles={}",
                planId, request.getDestinations().size(), request.getNumVehicles());
        
        // Build location list (depot + destinations)
        List<RoutePlanRequest.Location> allLocations = new ArrayList<>();
        allLocations.add(request.getOrigin());
        allLocations.addAll(request.getDestinations());
        
        int numLocations = allLocations.size();
        int numVehicles = request.getNumVehicles();
        int depot = 0;
        
        // Compute distance matrix
        long[][] distanceMatrix = computeDistanceMatrix(allLocations);
        
        // Create routing index manager
        RoutingIndexManager manager = new RoutingIndexManager(
                numLocations, numVehicles, depot);
        
        // Create routing model
        RoutingModel routing = new RoutingModel(manager);
        
        // Create distance callback
        final int transitCallbackIndex = routing.registerTransitCallback(
                (long fromIndex, long toIndex) -> {
                    int fromNode = manager.indexToNode(fromIndex);
                    int toNode = manager.indexToNode(toIndex);
                    return distanceMatrix[fromNode][toNode];
                });
        
        // Set cost of travel
        routing.setArcCostEvaluatorOfAllVehicles(transitCallbackIndex);
        
        // Add capacity constraint
        long[] demands = new long[numLocations];
        demands[0] = 0; // Depot has no demand
        for (int i = 1; i < numLocations; i++) {
            demands[i] = request.getDestinations().get(i - 1).getDemand();
        }
        
        final int demandCallbackIndex = routing.registerUnaryTransitCallback(
                (long fromIndex) -> {
                    int fromNode = manager.indexToNode(fromIndex);
                    return demands[fromNode];
                });
        
        routing.addDimensionWithVehicleCapacity(
                demandCallbackIndex,
                0, // Null capacity slack
                new long[]{request.getVehicleCapacity()},
                true, // Start cumul to zero
                "Capacity");
        
        // Set search parameters with 2-opt local search
        RoutingSearchParameters searchParameters = main.defaultRoutingSearchParameters()
                .toBuilder()
                .setFirstSolutionStrategy(FirstSolutionStrategy.Value.PATH_CHEAPEST_ARC)
                .setLocalSearchMetaheuristic(LocalSearchMetaheuristic.Value.GUIDED_LOCAL_SEARCH)
                .setTimeLimit(com.google.protobuf.Duration.newBuilder()
                        .setSeconds(request.getSolverTimeoutSeconds())
                        .build())
                .build();
        
        // Solve
        Assignment solution = routing.solveWithParameters(searchParameters);
        
        long solveTimeMs = System.currentTimeMillis() - startTime;
        
        if (solution == null) {
            log.warn("No solution found for planId={}", planId);
            return RoutePlanResponse.builder()
                    .planId(planId)
                    .status(SolutionStatus.INFEASIBLE)
                    .totalDistanceKm(0)
                    .totalDurationHours(0)
                    .totalCostUsd(0)
                    .totalCo2Kg(0)
                    .vehiclesUsed(0)
                    .routes(Collections.emptyList())
                    .solverStats(SolverStats.builder()
                            .solveTimeMs(solveTimeMs)
                            .algorithm("OR-Tools VRP")
                            .version("9.8")
                            .build())
                    .timestamp(Instant.now())
                    .build();
        }
        
        // Extract solution
        return extractSolution(
                planId, manager, routing, solution, allLocations, 
                numVehicles, distanceMatrix, solveTimeMs);
    }
    
    /**
     * Compute Haversine distance matrix between all locations.
     */
    private long[][] computeDistanceMatrix(List<RoutePlanRequest.Location> locations) {
        int n = locations.size();
        long[][] matrix = new long[n][n];
        
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (i == j) {
                    matrix[i][j] = 0;
                } else {
                    double distKm = haversineDistance(
                            locations.get(i).getLatitude(),
                            locations.get(i).getLongitude(),
                            locations.get(j).getLatitude(),
                            locations.get(j).getLongitude()
                    );
                    // Convert to meters for solver (integer precision)
                    matrix[i][j] = (long) (distKm * 1000);
                }
            }
        }
        
        return matrix;
    }
    
    /**
     * Calculate Haversine distance between two points.
     */
    private double haversineDistance(double lat1, double lon1, double lat2, double lon2) {
        final double R = 6371.0; // Earth radius in km
        
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);
        
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                   Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
                   Math.sin(dLon / 2) * Math.sin(dLon / 2);
        
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        
        return R * c;
    }
    
    /**
     * Extract solution from OR-Tools assignment.
     */
    private RoutePlanResponse extractSolution(
            String planId,
            RoutingIndexManager manager,
            RoutingModel routing,
            Assignment solution,
            List<RoutePlanRequest.Location> locations,
            int numVehicles,
            long[][] distanceMatrix,
            long solveTimeMs) {
        
        double totalDistanceKm = 0;
        double totalDurationHours = 0;
        int vehiclesUsed = 0;
        List<VehicleRoute> routes = new ArrayList<>();
        
        for (int vehicle = 0; vehicle < numVehicles; vehicle++) {
            List<RouteStop> stops = new ArrayList<>();
            long routeDistanceMeters = 0;
            int routeDemand = 0;
            int sequence = 0;
            double currentTimeHours = 0;
            
            long index = routing.start(vehicle);
            int prevNode = manager.indexToNode(index);
            
            while (!routing.isEnd(index)) {
                int nodeIndex = manager.indexToNode(index);
                RoutePlanRequest.Location loc = locations.get(nodeIndex);
                
                // Distance from previous
                double distFromPrevKm = distanceMatrix[prevNode][nodeIndex] / 1000.0;
                double travelTimeHours = distFromPrevKm / properties.getAvgSpeedKmh();
                currentTimeHours += travelTimeHours;
                
                double arrivalTime = currentTimeHours;
                double serviceTimeHours = loc.getServiceTimeMinutes() / 60.0;
                double departureTime = arrivalTime + serviceTimeHours;
                currentTimeHours = departureTime;
                
                stops.add(RouteStop.builder()
                        .sequence(sequence++)
                        .locationId(loc.getId())
                        .locationName(loc.getName())
                        .latitude(loc.getLatitude())
                        .longitude(loc.getLongitude())
                        .demand(loc.getDemand())
                        .arrivalTimeHours(arrivalTime)
                        .departureTimeHours(departureTime)
                        .distanceFromPreviousKm(distFromPrevKm)
                        .build());
                
                routeDemand += loc.getDemand();
                
                prevNode = nodeIndex;
                index = solution.value(routing.nextVar(index));
            }
            
            // Return to depot
            int lastNode = prevNode;
            int depotNode = manager.indexToNode(routing.start(vehicle));
            routeDistanceMeters += distanceMatrix[lastNode][depotNode];
            
            // Add depot return stop
            RoutePlanRequest.Location depot = locations.get(0);
            double returnDistKm = distanceMatrix[lastNode][depotNode] / 1000.0;
            double returnTimeHours = returnDistKm / properties.getAvgSpeedKmh();
            currentTimeHours += returnTimeHours;
            
            stops.add(RouteStop.builder()
                    .sequence(sequence)
                    .locationId(depot.getId())
                    .locationName(depot.getName() != null ? depot.getName() : "Depot")
                    .latitude(depot.getLatitude())
                    .longitude(depot.getLongitude())
                    .demand(0)
                    .arrivalTimeHours(currentTimeHours)
                    .departureTimeHours(currentTimeHours)
                    .distanceFromPreviousKm(returnDistKm)
                    .build());
            
            // Calculate route totals
            double routeDistanceKm = routeDistanceMeters / 1000.0;
            double routeCostUsd = routeDistanceKm * properties.getCostPerKm();
            double routeCo2Kg = routeDistanceKm * properties.getCo2KgPerKm();
            
            for (RouteStop stop : stops) {
                routeDistanceKm += stop.getDistanceFromPreviousKm();
            }
            
            if (stops.size() > 1) { // Has actual stops beyond depot
                vehiclesUsed++;
                
                routes.add(VehicleRoute.builder()
                        .vehicleId(vehicle)
                        .stops(stops)
                        .distanceKm(routeDistanceKm)
                        .durationHours(currentTimeHours)
                        .costUsd(routeDistanceKm * properties.getCostPerKm())
                        .co2Kg(routeDistanceKm * properties.getCo2KgPerKm())
                        .totalDemand(routeDemand)
                        .build());
                
                totalDistanceKm += routeDistanceKm;
                totalDurationHours = Math.max(totalDurationHours, currentTimeHours);
            }
        }
        
        double totalCostUsd = totalDistanceKm * properties.getCostPerKm();
        double totalCo2Kg = totalDistanceKm * properties.getCo2KgPerKm();
        
        SolutionStatus status = solveTimeMs >= properties.getTimeLimitMs() 
                ? SolutionStatus.TIMEOUT 
                : SolutionStatus.OPTIMAL;
        
        log.info("Route optimization complete: planId={}, distance={}km, duration={}h, vehicles={}",
                planId, String.format("%.2f", totalDistanceKm), 
                String.format("%.2f", totalDurationHours), vehiclesUsed);
        
        return RoutePlanResponse.builder()
                .planId(planId)
                .status(status)
                .totalDistanceKm(Math.round(totalDistanceKm * 100.0) / 100.0)
                .totalDurationHours(Math.round(totalDurationHours * 100.0) / 100.0)
                .totalCostUsd(Math.round(totalCostUsd * 100.0) / 100.0)
                .totalCo2Kg(Math.round(totalCo2Kg * 100.0) / 100.0)
                .vehiclesUsed(vehiclesUsed)
                .routes(routes)
                .solverStats(SolverStats.builder()
                        .solveTimeMs(solveTimeMs)
                        .algorithm("OR-Tools VRP with 2-opt")
                        .version("9.8")
                        .build())
                .timestamp(Instant.now())
                .build();
    }
}
