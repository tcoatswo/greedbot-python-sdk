use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::f64::consts::PI;

/// Standard Normal Cumulative Distribution Function (CDF)
#[inline(always)]
pub fn norm_cdf(x: f64) -> f64 {
    0.5 * (1.0 + erf(x / std::f64::consts::SQRT_2))
}

/// Standard Normal Probability Density Function (PDF)
#[inline(always)]
pub fn norm_pdf(x: f64) -> f64 {
    (-0.5 * x * x).exp() / (2.0 * PI).sqrt()
}

/// Fast Approximation of the Error Function (erf) - Abramowitz & Stegun 7.1.26
#[inline(always)]
pub fn erf(x: f64) -> f64 {
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

#[repr(C)]
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
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

/// Analytical Black-Scholes Greeks Engine
#[inline(always)]
pub fn calculate_greeks(
    spot: f64,
    strike: f64,
    dte_years: f64,
    rate: f64,
    div_yield: f64,
    iv: f64,
    is_call: bool,
) -> OptionGreeks {
    if dte_years <= 0.0 || iv <= 0.0 || spot <= 0.0 || strike <= 0.0 {
        let intrinsic = if is_call {
            (spot - strike).max(0.0)
        } else {
            (strike - spot).max(0.0)
        };
        return OptionGreeks {
            price: intrinsic,
            delta: if is_call { if spot > strike { 1.0 } else { 0.0 } } else { if spot < strike { -1.0 } else { 0.0 } },
            gamma: 0.0,
            vega: 0.0,
            theta: 0.0,
            rho: 0.0,
            vanna: 0.0,
            volga: 0.0,
            iv,
        };
    }

    let sqrt_t = dte_years.sqrt();
    let d1 = ((spot / strike).ln() + (rate - div_yield + 0.5 * iv * iv) * dte_years) / (iv * sqrt_t);
    let d2 = d1 - iv * sqrt_t;

    let df_q = (-div_yield * dte_years).exp();
    let df_r = (-rate * dte_years).exp();

    let nd1 = norm_cdf(d1);
    let nd2 = norm_cdf(d2);
    let n_prime_d1 = norm_pdf(d1);

    let (price, delta, rho) = if is_call {
        let p = spot * df_q * nd1 - strike * df_r * nd2;
        let d = df_q * nd1;
        let r = strike * dte_years * df_r * nd2 / 100.0;
        (p, d, r)
    } else {
        let n_minus_d1 = norm_cdf(-d1);
        let n_minus_d2 = norm_cdf(-d2);
        let p = strike * df_r * n_minus_d2 - spot * df_q * n_minus_d1;
        let d = df_q * (nd1 - 1.0);
        let r = -strike * dte_years * df_r * n_minus_d2 / 100.0;
        (p, d, r)
    };

    let gamma = (df_q * n_prime_d1) / (spot * iv * sqrt_t);
    let vega = (spot * df_q * sqrt_t * n_prime_d1) / 100.0;

    let theta_term1 = -(spot * df_q * n_prime_d1 * iv) / (2.0 * sqrt_t);
    let theta = if is_call {
        (theta_term1 - rate * strike * df_r * nd2 + div_yield * spot * df_q * nd1) / 365.0
    } else {
        (theta_term1 + rate * strike * df_r * norm_cdf(-d2) - div_yield * spot * df_q * norm_cdf(-d1)) / 365.0
    };

    // Higher-order Greeks
    let vanna = (-df_q * n_prime_d1 * d2 / iv) / 100.0;
    let volga = (vega * d1 * d2 / iv) / 100.0;

    OptionGreeks {
        price,
        delta,
        gamma,
        vega,
        theta,
        rho,
        vanna,
        volga,
        iv,
    }
}

/// Newton-Raphson + Bisection Implied Volatility Solver
pub fn solve_implied_volatility(
    spot: f64,
    strike: f64,
    dte_years: f64,
    rate: f64,
    div_yield: f64,
    market_price: f64,
    is_call: bool,
) -> f64 {
    let intrinsic = if is_call {
        (spot - strike).max(0.0)
    } else {
        (strike - spot).max(0.0)
    };

    if market_price <= intrinsic {
        return 0.0001;
    }

    let mut sigma = (2.0 * PI / dte_years).sqrt() * (market_price / spot);
    if sigma <= 0.0 || sigma.is_nan() {
        sigma = 0.25;
    }

    // Newton-Raphson iterations
    for _ in 0..64 {
        let greeks = calculate_greeks(spot, strike, dte_years, rate, div_yield, sigma, is_call);
        let diff = greeks.price - market_price;
        if diff.abs() < 1e-6 {
            return sigma;
        }
        let vega_raw = greeks.vega * 100.0;
        if vega_raw.abs() > 1e-8 {
            let next_sigma = sigma - diff / vega_raw;
            if next_sigma > 0.001 && next_sigma < 10.0 {
                sigma = next_sigma;
                continue;
            }
        }
        break;
    }

    // Robust Bisection Fallback
    let mut low = 0.0001;
    let mut high = 10.0;
    for _ in 0..40 {
        let mid = (low + high) * 0.5;
        let g = calculate_greeks(spot, strike, dte_years, rate, div_yield, mid, is_call);
        if (g.price - market_price).abs() < 1e-5 {
            return mid;
        }
        if g.price > market_price {
            high = mid;
        } else {
            low = mid;
        }
    }
    (low + high) * 0.5
}

// ==========================================
// C-ABI Export for Fast Foreign Function Call
// ==========================================

#[no_mangle]
pub extern "C" fn greedbot_c_greeks(
    spot: f64,
    strike: f64,
    dte_days: f64,
    rate: f64,
    div_yield: f64,
    iv: f64,
    is_call: bool,
    out: *mut OptionGreeks,
) -> i32 {
    if out.is_null() {
        return -1;
    }
    let dte_years = dte_days / 365.0;
    let res = calculate_greeks(spot, strike, dte_years, rate, div_yield, iv, is_call);
    unsafe {
        *out = res;
    }
    0
}

#[no_mangle]
pub extern "C" fn greedbot_c_solve_iv(
    spot: f64,
    strike: f64,
    dte_days: f64,
    rate: f64,
    div_yield: f64,
    market_price: f64,
    is_call: bool,
) -> f64 {
    let dte_years = dte_days / 365.0;
    solve_implied_volatility(spot, strike, dte_years, rate, div_yield, market_price, is_call)
}

#[no_mangle]
pub extern "C" fn greedbot_c_batch_greeks(
    spots: *const f64,
    strikes: *const f64,
    dte_days: *const f64,
    rates: *const f64,
    div_yields: *const f64,
    ivs: *const f64,
    is_calls: *const u8,
    count: usize,
    out: *mut OptionGreeks,
) -> i32 {
    if spots.is_null() || strikes.is_null() || dte_days.is_null() || ivs.is_null() || out.is_null() {
        return -1;
    }

    let spots_slice = unsafe { std::slice::from_raw_parts(spots, count) };
    let strikes_slice = unsafe { std::slice::from_raw_parts(strikes, count) };
    let dte_slice = unsafe { std::slice::from_raw_parts(dte_days, count) };
    let rates_slice = if rates.is_null() { None } else { Some(unsafe { std::slice::from_raw_parts(rates, count) }) };
    let divs_slice = if div_yields.is_null() { None } else { Some(unsafe { std::slice::from_raw_parts(div_yields, count) }) };
    let ivs_slice = unsafe { std::slice::from_raw_parts(ivs, count) };
    let calls_slice = unsafe { std::slice::from_raw_parts(is_calls, count) };

    let results: Vec<OptionGreeks> = (0..count)
        .into_par_iter()
        .map(|i| {
            let spot = spots_slice[i];
            let strike = strikes_slice[i];
            let dte_years = dte_slice[i] / 365.0;
            let rate = rates_slice.map(|r| r[i]).unwrap_or(0.045);
            let div_yield = divs_slice.map(|d| d[i]).unwrap_or(0.0);
            let iv = ivs_slice[i];
            let is_call = calls_slice[i] != 0;
            calculate_greeks(spot, strike, dte_years, rate, div_yield, iv, is_call)
        })
        .collect();

    unsafe {
        std::ptr::copy_nonoverlapping(results.as_ptr(), out, count);
    }
    0
}
