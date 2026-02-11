//! Parallel simulation runner using rayon.

use rayon::prelude::*;

use crate::evm::EVMStrategy;
use crate::simulation::engine::{SimulationEngine, SimulationError};
use crate::types::config::SimulationConfig;
use crate::types::result::{BatchSimulationResult, LightweightSimResult};

/// Configuration for a batch of simulations.
pub struct SimulationBatchConfig {
    /// Bytecode for the submission strategy
    pub submission_bytecode: Vec<u8>,
    /// Bytecode for the baseline strategy
    pub baseline_bytecode: Vec<u8>,
    /// List of simulation configs (one per simulation)
    pub configs: Vec<SimulationConfig>,
    /// Number of parallel workers (None = auto-detect)
    pub n_workers: Option<usize>,
}

/// Configuration for a batch of n-way simulations.
pub struct NWaySimulationBatchConfig {
    /// Bytecodes for all strategies
    pub strategy_bytecodes: Vec<Vec<u8>>,
    /// List of simulation configs (one per simulation)
    pub configs: Vec<SimulationConfig>,
    /// Number of parallel workers (None = auto-detect)
    pub n_workers: Option<usize>,
}

/// Run multiple simulations in parallel.
pub fn run_simulations_parallel(
    batch_config: SimulationBatchConfig,
) -> Result<BatchSimulationResult, SimulationError> {
    // Configure thread pool
    let n_workers = batch_config.n_workers.unwrap_or_else(|| {
        rayon::current_num_threads().min(8)
    });

    // Build custom thread pool if needed
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(n_workers)
        .build()
        .map_err(|e| SimulationError::InvalidConfig(format!("Failed to create thread pool: {}", e)))?;

    // Clone bytecodes for each worker (they need their own EVM instances)
    let submission_bytecode = batch_config.submission_bytecode;
    let baseline_bytecode = batch_config.baseline_bytecode;

    // Run simulations in parallel
    let results: Result<Vec<LightweightSimResult>, SimulationError> = pool.install(|| {
        batch_config.configs
            .into_par_iter()
            .map(|config| {
                // Create fresh EVM strategies for this worker
                let submission = EVMStrategy::new(
                    submission_bytecode.clone(),
                    "Submission".to_string(),
                ).map_err(|e| SimulationError::EVMError(e.to_string()))?;

                let baseline = EVMStrategy::new(
                    baseline_bytecode.clone(),
                    "Baseline".to_string(),
                ).map_err(|e| SimulationError::EVMError(e.to_string()))?;

                let mut engine = SimulationEngine::new(config);
                engine.run(submission, baseline)
            })
            .collect()
    });

    let results = results?;

    // Extract strategy names from first result
    let strategies = if let Some(first) = results.first() {
        first.strategies.clone()
    } else {
        Vec::new()
    };

    Ok(BatchSimulationResult { results, strategies })
}

/// Run a single simulation (non-parallel).
pub fn run_simulation(
    submission_bytecode: Vec<u8>,
    baseline_bytecode: Vec<u8>,
    config: SimulationConfig,
) -> Result<LightweightSimResult, SimulationError> {
    let submission = EVMStrategy::new(submission_bytecode, "Submission".to_string())
        .map_err(|e| SimulationError::EVMError(e.to_string()))?;

    let baseline = EVMStrategy::new(baseline_bytecode, "Baseline".to_string())
        .map_err(|e| SimulationError::EVMError(e.to_string()))?;

    let mut engine = SimulationEngine::new(config);
    engine.run(submission, baseline)
}

/// Run multiple n-way simulations in parallel.
pub fn run_n_way_simulations_parallel(
    batch_config: NWaySimulationBatchConfig,
) -> Result<BatchSimulationResult, SimulationError> {
    // Validate we have at least 2 strategies
    if batch_config.strategy_bytecodes.len() < 2 {
        return Err(SimulationError::InvalidConfig(
            "At least 2 strategies required for n-way match".to_string(),
        ));
    }

    // Validate strategy count is within limits
    if batch_config.strategy_bytecodes.len() > 10 {
        return Err(SimulationError::InvalidConfig(
            "Maximum 10 strategies allowed for n-way match".to_string(),
        ));
    }

    // Configure thread pool
    let n_workers = batch_config.n_workers.unwrap_or_else(|| {
        rayon::current_num_threads().min(8)
    });

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(n_workers)
        .build()
        .map_err(|e| SimulationError::InvalidConfig(format!("Failed to create thread pool: {}", e)))?;

    // Clone bytecodes for sharing across workers
    let strategy_bytecodes = batch_config.strategy_bytecodes;

    // Run simulations in parallel
    let results: Result<Vec<LightweightSimResult>, SimulationError> = pool.install(|| {
        batch_config.configs
            .into_par_iter()
            .map(|config| {
                // Create fresh EVM strategies for this worker
                let strategies: Result<Vec<EVMStrategy>, SimulationError> = strategy_bytecodes
                    .iter()
                    .enumerate()
                    .map(|(idx, bytecode)| {
                        EVMStrategy::new(
                            bytecode.clone(),
                            format!("Strategy_{}", idx),
                        ).map_err(|e| SimulationError::EVMError(e.to_string()))
                    })
                    .collect();

                let strategies = strategies?;
                let mut engine = SimulationEngine::new(config);
                engine.run_n_way(strategies)
            })
            .collect()
    });

    let results = results?;

    // Extract strategy names from first result
    let strategies = if let Some(first) = results.first() {
        first.strategies.clone()
    } else {
        Vec::new()
    };

    Ok(BatchSimulationResult { results, strategies })
}

#[cfg(test)]
mod tests {
    use super::*;

    // Full tests require EVM bytecode - see integration tests
}
