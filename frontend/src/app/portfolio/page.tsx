"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { PortfolioItem, Trade } from "@/lib/types";

function formatETH(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(2)}K ETH`;
  return `${value.toFixed(4)} ETH`;
}

function formatUSD(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(2)}`;
}

const ETH_PRICE = 2500; // placeholder

export default function PortfolioPage() {
  const [wallet, setWallet] = useState("");
  const [connected, setConnected] = useState(false);
  const [holdings, setHoldings] = useState<PortfolioItem[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(false);

  const loadPortfolio = async (address: string) => {
    setLoading(true);
    try {
      const [h, t] = await Promise.all([
        api.trading.portfolio(address),
        api.trading.history(address, 20),
      ]);
      setHoldings(h);
      setTrades(t);
      setConnected(true);
    } catch {
      setHoldings([]);
      setTrades([]);
    } finally {
      setLoading(false);
    }
  };

  // Calculate totals
  const totalInvested = holdings.reduce((s, h) => s + h.total_invested_eth, 0);
  const totalUnrealized = holdings.reduce(
    (s, h) => s + (h.unrealized_pnl_eth ?? 0),
    0
  );
  const totalRealized = holdings.reduce((s, h) => s + h.realized_pnl_eth, 0);
  const totalValue = holdings.reduce(
    (s, h) => s + h.balance * (h.current_price_eth ?? 0),
    0
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Portfolio</h1>
        <p className="text-gray-400 mt-1">
          Track your soul token holdings and P&amp;L
        </p>
      </div>

      {/* Wallet Input */}
      <div className="rounded-xl border border-gray-800 p-6">
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Enter wallet address (0x...)"
            value={wallet}
            onChange={(e) => setWallet(e.target.value)}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-sm font-mono placeholder-gray-500 focus:outline-none focus:border-nile-500"
          />
          <button
            onClick={() => wallet.length === 42 && loadPortfolio(wallet)}
            disabled={wallet.length !== 42 || loading}
            className="px-6 py-2 bg-nile-500 hover:bg-nile-600 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "Loading..." : "View Portfolio"}
          </button>
        </div>
      </div>

      {connected && (
        <>
          {/* Portfolio Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-xl border border-gray-800 p-4">
              <p className="text-xs text-gray-500">Total Value</p>
              <p className="text-xl font-mono mt-1">{formatETH(totalValue)}</p>
              <p className="text-xs text-gray-500">
                ~{formatUSD(totalValue * ETH_PRICE)}
              </p>
            </div>
            <div className="rounded-xl border border-gray-800 p-4">
              <p className="text-xs text-gray-500">Total Invested</p>
              <p className="text-xl font-mono mt-1">
                {formatETH(totalInvested)}
              </p>
            </div>
            <div className="rounded-xl border border-gray-800 p-4">
              <p className="text-xs text-gray-500">Unrealized P&amp;L</p>
              <p
                className={`text-xl font-mono mt-1 ${
                  totalUnrealized >= 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {totalUnrealized >= 0 ? "+" : ""}
                {formatETH(totalUnrealized)}
              </p>
            </div>
            <div className="rounded-xl border border-gray-800 p-4">
              <p className="text-xs text-gray-500">Realized P&amp;L</p>
              <p
                className={`text-xl font-mono mt-1 ${
                  totalRealized >= 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {totalRealized >= 0 ? "+" : ""}
                {formatETH(totalRealized)}
              </p>
            </div>
          </div>

          {/* Holdings Table */}
          <div>
            <h2 className="text-xl font-semibold mb-3">Holdings</h2>
            {holdings.length === 0 ? (
              <div className="rounded-xl border border-gray-800 p-8 text-center text-gray-500">
                No holdings found for this wallet
              </div>
            ) : (
              <div className="rounded-xl border border-gray-800 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
                      <th className="text-left py-3 px-4">Token</th>
                      <th className="text-right py-3 px-4">Balance</th>
                      <th className="text-right py-3 px-4">Avg Buy</th>
                      <th className="text-right py-3 px-4">Current</th>
                      <th className="text-right py-3 px-4">Invested</th>
                      <th className="text-right py-3 px-4">Unrealized</th>
                      <th className="text-right py-3 px-4">Realized</th>
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map((h) => (
                      <tr
                        key={h.id}
                        className="border-b border-gray-800/50 hover:bg-gray-900/30"
                      >
                        <td className="py-3 px-4 font-mono text-nile-400">
                          {h.token_symbol ? `$${h.token_symbol}` : "???"}
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {h.balance.toFixed(2)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {h.avg_buy_price_eth.toFixed(6)} ETH
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {h.current_price_eth?.toFixed(6) ?? "--"} ETH
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {h.total_invested_eth.toFixed(4)} ETH
                        </td>
                        <td
                          className={`py-3 px-4 text-right font-mono ${
                            (h.unrealized_pnl_eth ?? 0) >= 0
                              ? "text-green-400"
                              : "text-red-400"
                          }`}
                        >
                          {h.unrealized_pnl_eth != null
                            ? `${h.unrealized_pnl_eth >= 0 ? "+" : ""}${h.unrealized_pnl_eth.toFixed(4)}`
                            : "--"}
                        </td>
                        <td
                          className={`py-3 px-4 text-right font-mono ${
                            h.realized_pnl_eth >= 0
                              ? "text-green-400"
                              : "text-red-400"
                          }`}
                        >
                          {h.realized_pnl_eth >= 0 ? "+" : ""}
                          {h.realized_pnl_eth.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Recent Trades */}
          <div>
            <h2 className="text-xl font-semibold mb-3">Recent Trades</h2>
            {trades.length === 0 ? (
              <div className="rounded-xl border border-gray-800 p-8 text-center text-gray-500">
                No trades found for this wallet
              </div>
            ) : (
              <div className="rounded-xl border border-gray-800 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
                      <th className="text-left py-3 px-4">Time</th>
                      <th className="text-center py-3 px-4">Side</th>
                      <th className="text-right py-3 px-4">Tokens</th>
                      <th className="text-right py-3 px-4">ETH</th>
                      <th className="text-right py-3 px-4">Price</th>
                      <th className="text-right py-3 px-4">Fee</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr
                        key={t.id}
                        className="border-b border-gray-800/50 hover:bg-gray-900/30"
                      >
                        <td className="py-3 px-4 text-gray-400 text-xs">
                          {new Date(t.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-xs ${
                              t.side === "buy"
                                ? "bg-green-500/20 text-green-400"
                                : "bg-red-500/20 text-red-400"
                            }`}
                          >
                            {t.side.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {t.token_amount.toFixed(2)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {t.eth_amount.toFixed(4)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          ${t.price_usd.toFixed(2)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-gray-500">
                          {t.fee_total_eth.toFixed(6)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {!connected && (
        <div className="rounded-xl border border-gray-800 p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">
            Enter your wallet address to view your portfolio
          </p>
          <p className="text-gray-500 text-sm">
            Track holdings, P&amp;L, and trade history across all soul tokens
          </p>
        </div>
      )}
    </div>
  );
}
