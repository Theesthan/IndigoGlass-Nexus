// =============================================================================
// IndigoGlass Nexus - Optimizer Application Entry Point
// =============================================================================
package com.indigoglass.optimizer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Main application class for the TSP-D optimizer service.
 */
@SpringBootApplication
public class OptimizerApplication {
    
    public static void main(String[] args) {
        SpringApplication.run(OptimizerApplication.class, args);
    }
}
