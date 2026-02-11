// =============================================================================
// IndigoGlass Nexus - Route Controller
// =============================================================================
package com.indigoglass.optimizer.controller;

import com.indigoglass.optimizer.dto.RoutePlanRequest;
import com.indigoglass.optimizer.dto.RoutePlanResponse;
import com.indigoglass.optimizer.service.RouteOptimizerService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * REST controller for route optimization endpoints.
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/routes")
@RequiredArgsConstructor
@Tag(name = "Route Optimization", description = "TSP-D route planning endpoints")
public class RouteController {
    
    private final RouteOptimizerService optimizerService;
    
    /**
     * Generate optimized route plan.
     *
     * @param request Route plan request with origin, destinations, and constraints
     * @return Optimized route plan with vehicle assignments and stops
     */
    @PostMapping("/plan")
    @Operation(
            summary = "Generate route plan",
            description = "Solves the Vehicle Routing Problem for given locations using OR-Tools"
    )
    public ResponseEntity<RoutePlanResponse> planRoute(
            @Valid @RequestBody RoutePlanRequest request) {
        
        log.info("Route plan request: destinations={}, vehicles={}",
                request.getDestinations().size(), request.getNumVehicles());
        
        RoutePlanResponse response = optimizerService.solve(request);
        
        return ResponseEntity.ok(response);
    }
    
    /**
     * Health check endpoint.
     *
     * @return Health status
     */
    @GetMapping("/health")
    @Operation(summary = "Health check", description = "Check optimizer service health")
    public ResponseEntity<HealthResponse> health() {
        return ResponseEntity.ok(new HealthResponse("healthy", "Optimizer service is running"));
    }
    
    /**
     * Simple health response.
     */
    public record HealthResponse(String status, String message) {}
}
