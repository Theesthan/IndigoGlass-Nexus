// =============================================================================
// IndigoGlass Nexus - Optimizer Configuration Properties
// =============================================================================
package com.indigoglass.optimizer.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * Configuration properties for the optimizer service.
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "optimizer")
public class OptimizerProperties {
    
    /**
     * Time limit for solver in milliseconds.
     */
    private long timeLimitMs = 30000;
    
    /**
     * Maximum number of locations per request.
     */
    private int maxLocations = 100;
    
    /**
     * Default vehicle capacity in units.
     */
    private int defaultVehicleCapacity = 1000;
    
    /**
     * CO2 emission factor (kg per km).
     */
    private double co2KgPerKm = 0.12;
    
    /**
     * Cost per km in USD.
     */
    private double costPerKm = 0.75;
    
    /**
     * Average speed in km/h for time estimation.
     */
    private double avgSpeedKmh = 50;
}
