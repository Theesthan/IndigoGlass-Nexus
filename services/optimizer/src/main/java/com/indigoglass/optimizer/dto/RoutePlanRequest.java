// =============================================================================
// IndigoGlass Nexus - Route Plan Request DTO
// =============================================================================
package com.indigoglass.optimizer.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import lombok.Data;

import java.util.List;

/**
 * Request DTO for route planning.
 */
@Data
public class RoutePlanRequest {
    
    /**
     * Origin location (depot).
     */
    @NotNull(message = "Origin is required")
    @Valid
    private Location origin;
    
    /**
     * List of destination stops.
     */
    @NotNull(message = "Destinations are required")
    @Size(min = 1, max = 100, message = "Destinations must be between 1 and 100")
    @Valid
    private List<Location> destinations;
    
    /**
     * Number of vehicles available.
     */
    @Min(value = 1, message = "At least 1 vehicle required")
    @Max(value = 50, message = "Maximum 50 vehicles")
    private int numVehicles = 1;
    
    /**
     * Vehicle capacity in units.
     */
    @Min(value = 1, message = "Vehicle capacity must be positive")
    private int vehicleCapacity = 1000;
    
    /**
     * Whether to optimize for distance (true) or time (false).
     */
    private boolean optimizeForDistance = true;
    
    /**
     * Maximum solver time in seconds.
     */
    @Min(value = 1, message = "Solver timeout must be at least 1 second")
    @Max(value = 300, message = "Solver timeout cannot exceed 300 seconds")
    private int solverTimeoutSeconds = 30;
    
    /**
     * Location data.
     */
    @Data
    public static class Location {
        
        @NotBlank(message = "Location ID is required")
        private String id;
        
        private String name;
        
        @NotNull(message = "Latitude is required")
        @DecimalMin(value = "-90.0", message = "Latitude must be >= -90")
        @DecimalMax(value = "90.0", message = "Latitude must be <= 90")
        private Double latitude;
        
        @NotNull(message = "Longitude is required")
        @DecimalMin(value = "-180.0", message = "Longitude must be >= -180")
        @DecimalMax(value = "180.0", message = "Longitude must be <= 180")
        private Double longitude;
        
        /**
         * Demand at this location (units to deliver/pickup).
         */
        @Min(value = 0, message = "Demand cannot be negative")
        private int demand = 0;
        
        /**
         * Service time at this location in minutes.
         */
        @Min(value = 0, message = "Service time cannot be negative")
        private int serviceTimeMinutes = 15;
    }
}
