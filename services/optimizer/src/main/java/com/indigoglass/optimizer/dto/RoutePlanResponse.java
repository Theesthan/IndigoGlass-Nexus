// =============================================================================
// IndigoGlass Nexus - Route Plan Response DTO
// =============================================================================
package com.indigoglass.optimizer.dto;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;
import java.util.List;

/**
 * Response DTO for route planning.
 */
@Data
@Builder
public class RoutePlanResponse {
    
    /**
     * Unique plan ID.
     */
    private String planId;
    
    /**
     * Solution status.
     */
    private SolutionStatus status;
    
    /**
     * Total distance in kilometers.
     */
    private double totalDistanceKm;
    
    /**
     * Total estimated duration in hours.
     */
    private double totalDurationHours;
    
    /**
     * Total cost in USD.
     */
    private double totalCostUsd;
    
    /**
     * Total CO2 emissions in kg.
     */
    private double totalCo2Kg;
    
    /**
     * Number of vehicles used.
     */
    private int vehiclesUsed;
    
    /**
     * Routes for each vehicle.
     */
    private List<VehicleRoute> routes;
    
    /**
     * Solver statistics.
     */
    private SolverStats solverStats;
    
    /**
     * Timestamp.
     */
    private Instant timestamp;
    
    /**
     * Solution status enum.
     */
    public enum SolutionStatus {
        OPTIMAL,
        FEASIBLE,
        INFEASIBLE,
        NOT_SOLVED,
        TIMEOUT
    }
    
    /**
     * Route for a single vehicle.
     */
    @Data
    @Builder
    public static class VehicleRoute {
        
        private int vehicleId;
        private List<RouteStop> stops;
        private double distanceKm;
        private double durationHours;
        private double costUsd;
        private double co2Kg;
        private int totalDemand;
    }
    
    /**
     * A stop on a route.
     */
    @Data
    @Builder
    public static class RouteStop {
        
        private int sequence;
        private String locationId;
        private String locationName;
        private double latitude;
        private double longitude;
        private int demand;
        private double arrivalTimeHours;
        private double departureTimeHours;
        private double distanceFromPreviousKm;
    }
    
    /**
     * Solver statistics.
     */
    @Data
    @Builder
    public static class SolverStats {
        
        private long solveTimeMs;
        private int iterations;
        private String algorithm;
        private String version;
    }
}
