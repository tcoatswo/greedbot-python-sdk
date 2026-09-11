use clap::{Parser, Subcommand};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::f64::consts::PI;
use std::time::Instant;

/// Standard Normal Cumulative Distribution Function (CDF)
#[inline(always)]
fn norm_cdf(x: f64) -> f64 {
    0.5 * (1.0 + erf(x / std::f64::consts::SQRT_2))
}

/// Standard Normal Probability Density Function (PDF)
#[inline(always)]
fn norm_pdf(x: f64) -> f64 {
    (-0.5 * x * x).exp() / (2.0 * PI).sqrt()
}

/// Approximation of the Error Function (erf)
#[inline(always)]
fn erf(x: f64) -> f64 {
    // Abramowitz and Stegun formula 7.1.26
    let a1 = 0.254829592;
    let a2 = -0.284496736;
    let a3 = 1.421413741;
    let a4 = -1.453152027;
    let a5 = 1.061405429;
    let p = 0.3275911;

    let sign = if x < 0.0 { -1.0 } else { 1.0 };
    let abs_x = x.abs();

    let t = 1.0 / (1.0 + p * abs_x);
    let y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * (-abs_x * abs_x).exp();

    sign * y
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptionGreeks {
    pub price: f64,
    pub delta: f64,
    pub gamma: f64,
    pub vega: f64,
    pub theta: f64,
    pub rho: f64,
    pub vanna: f64,
    pub volga: f64,
    pub iv: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum OptionType {
    Call,
    Put,
}

impl OptionType {
    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "p" | "put" => OptionType::Put,
            _ => OptionType::Call,
        }
    }
}

/// Black-Scholes analytical price & Greeks calculator
pub fn calculate_greeks(
    spot: f64,
    strike: f64,
    rate: f64,
    time_to_exp: f64,
    vol: f64,
    option_type: OptionType,
) -> OptionGreeks {
    if time_to_exp <= 0.0 || vol <= 0.0 || spot <= 0.0 || strike <= 0.0 {
        let intrinsic = match option_type {
            OptionType::Call => (spot - strike).max(0.0),
            OptionType::Put => (strike - spot).max(0.0),
        };
        return OptionGreeks {
            price: intrinsic,
            delta: if intrinsic > 0.0 { 1.0 } else { 0.0 },
            gamma: 0.0,
            vega: 0.0,
            theta: 0.0,
            rho: 0.0,
            vanna: 0.0,
            volga: 0.0,
            iv: vol,
        };
    }

    let sqrt_t = time_to_exp.sqrt();
    let d1 = ((spot / strike).ln() + (rate + 0.5 * vol * vol) * time_to_exp) / (vol * sqrt_t);
    let d2 = d1 - vol * sqrt_t;

    let nd1 = norm_cdf(d1);
    let nd2 = norm_cdf(d2);
    let n_prime_d1 = norm_pdf(d1);
    let df = (-rate * time_to_exp).exp();

    let (price, delta, rho) = match option_type {
        OptionType::Call => {
            let p = spot * nd1 - strike * df * nd2;
            let d = nd1;
            let r = strike * time_to_exp * df * nd2 / 100.0;
            (p, d, r)
        }
        OptionType::Put => {
            let n_neg_d1 = norm_cdf(-d1);
            let n_neg_d2 = norm_cdf(-d2);
            let p = strike * df * n_neg_d2 - spot * n_neg_d1;
            let d = nd1 - 1.0;
            let r = -strike * time_to_exp * df * n_neg_d2 / 100.0;
            (p, d, r)
        }
    };

    let gamma = n_prime_d1 / (spot * vol * sqrt_t);
    let vega = spot * sqrt_t * n_prime_d1 / 100.0; // Scaled per 1% vol
    let theta_annual = -spot * n_prime_d1 * vol / (2.0 * sqrt_t)
        - match option_type {
            OptionType::Call => rate * strike * df * nd2,
            OptionType::Put => -rate * strike * df * norm_cdf(-d2),
        };
    let theta = theta_annual / 365.0; // 1-day theta decay

    let vanna = -n_prime_d1 * d2 / vol / 100.0;
    let volga = vega * d1 * d2 / vol;

    OptionGreeks {
        price,
        delta,
        gamma,
        vega,
        theta,
        rho,
        vanna,
        volga,
        iv: vol,
    }
}

/// Numerical Implied Volatility Solver (Newton-Raphson with Bisection fallback)
pub fn solve_implied_vol(
    market_price: f64,
    spot: f64,
    strike: f64,
    rate: f64,
    time_to_exp: f64,
    option_type: OptionType,
) -> f64 {
    let mut vol = 0.30; // initial guess
    let max_iter = 50;
    let epsilon = 1e-6;

    let intrinsic = match option_type {
        OptionType::Call => (spot - strike).max(0.0),
        OptionType::Put => (strike - spot).max(0.0),
    };

    if market_price <= intrinsic {
        return 0.001;
    }

    // Newton-Raphson
    for _ in 0..max_iter {
        let greeks = calculate_greeks(spot, strike, rate, time_to_exp, vol, option_type);
        let diff = greeks.price - market_price;
        if diff.abs() < epsilon {
            return vol;
        }
        let vega_raw = greeks.vega * 100.0; // Unscaled
        if vega_raw < 1e-12 {
            break;
        }
        let next_vol = vol - diff / vega_raw;
        if next_vol <= 0.001 || next_vol >= 10.0 {
            break;
        }
        vol = next_vol;
    }

    // Bisection Fallback
    let mut low = 0.0001;
    let mut high = 5.0;
    for _ in 0..50 {
        let mid = 0.5 * (low + high);
        let price = calculate_greeks(spot, strike, rate, time_to_exp, mid, option_type).price;
        let diff = price - market_price;
        if diff.abs() < epsilon {
            return mid;
        }
        if diff > 0.0 {
            high = mid;
        } else {
            low = mid;
        }
    }
    0.5 * (low + high)
}

#[derive(Parser)]
#[command(name = "greedbot_quant")]
#[command(about = "Ultra-fast compiled quantitative options & volatility engine", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Calculate price and Greeks for a single contract
    Price {
        #[arg(long)]
        spot: f64,
        #[arg(long)]
        strike: f64,
        #[arg(long, default_value_t = 0.045)]
        rate: f64,
        #[arg(long)]
        dte: f64,
        #[arg(long)]
        vol: f64,
        #[arg(long, default_value = "call")]
        opt_type: String,
    },
    /// Solve Implied Volatility given market price
    SolveIv {
        #[arg(long)]
        market_price: f64,
        #[arg(long)]
        spot: f64,
        #[arg(long)]
        strike: f64,
        #[arg(long, default_value_t = 0.045)]
        rate: f64,
        #[arg(long)]
        dte: f64,
        #[arg(long, default_value = "call")]
        opt_type: String,
    },
    /// Benchmark throughput over N parallel contract evaluations
    Benchmark {
        #[arg(long, default_value_t = 100_000)]
        contracts: usize,
    },
    /// Generate a parallel Volatility Surface mesh
    Surface {
        #[arg(long)]
        spot: f64,
        #[arg(long, default_value_t = 0.045)]
        rate: f64,
        #[arg(long, default_value_t = 0.25)]
        base_vol: f64,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Price {
            spot,
            strike,
            rate,
            dte,
            vol,
            opt_type,
        } => {
            let t = dte / 365.0;
            let otype = OptionType::from_str(&opt_type);
            let greeks = calculate_greeks(spot, strike, rate, t, vol, otype);
            println!("{}", serde_json::to_string_pretty(&greeks).unwrap());
        }
        Commands::SolveIv {
            market_price,
            spot,
            strike,
            rate,
            dte,
            opt_type,
        } => {
            let t = dte / 365.0;
            let otype = OptionType::from_str(&opt_type);
            let iv = solve_implied_vol(market_price, spot, strike, rate, t, otype);
            let greeks = calculate_greeks(spot, strike, rate, t, iv, otype);
            println!("{}", serde_json::to_string_pretty(&greeks).unwrap());
        }
        Commands::Benchmark { contracts } => {
            println!("🚀 Running parallel benchmark on {} option contracts...", contracts);
            let spot = 580.0;
            let rate = 0.045;

            let test_cases: Vec<(f64, f64, f64, OptionType)> = (0..contracts)
                .map(|i| {
                    let strike = 500.0 + (i % 160) as f64;
                    let dte = 1.0 + (i % 90) as f64;
                    let vol = 0.15 + (i % 30) as f64 * 0.01;
                    let opt_type = if i % 2 == 0 { OptionType::Call } else { OptionType::Put };
                    (strike, dte, vol, opt_type)
                })
                .collect();

            let start = Instant::now();
            let results: Vec<OptionGreeks> = test_cases
                .par_iter()
                .map(|(strike, dte, vol, opt_type)| {
                    calculate_greeks(spot, *strike, rate, *dte / 365.0, *vol, *opt_type)
                })
                .collect();
            let elapsed = start.elapsed();

            let total_micros = elapsed.as_micros() as f64;
            let per_contract_ns = (elapsed.as_nanos() as f64) / (contracts as f64);
            let throughput = (contracts as f64) / elapsed.as_secs_f64();

            println!("✅ Processed {} contracts in {:.2} ms", results.len(), total_micros / 1000.0);
            println!("⚡ Average Latency : {:.1} ns per contract", per_contract_ns);
            println!("🔥 Throughput      : {:.0} contracts/second", throughput);
        }
        Commands::Surface { spot, rate, base_vol } => {
            let strikes: Vec<f64> = (-10..=10).map(|i| spot * (1.0 + (i as f64) * 0.02)).collect();
            let dtes: Vec<f64> = vec![7.0, 14.0, 30.0, 45.0, 60.0, 90.0, 180.0];

            let mut surface = Vec::new();
            for dte in &dtes {
                let row: Vec<OptionGreeks> = strikes
                    .par_iter()
                    .map(|strike| {
                        // Parabolic volatility smile formula
                        let moneyness = (strike / spot).ln();
                        let vol = base_vol + 0.15 * moneyness * moneyness;
                        calculate_greeks(spot, *strike, rate, *dte / 365.0, vol, OptionType::Call)
                    })
                    .collect();
                surface.push(row);
            }

            println!("{}", serde_json::to_string(&surface).unwrap());
        }
    }
}
