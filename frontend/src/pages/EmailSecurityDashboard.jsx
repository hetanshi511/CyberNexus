import React, { useState } from 'react';
import {
    ShieldCheck, ShieldAlert, ShieldX, Mail, Link as LinkIcon,
    Loader2, AlertTriangle, RefreshCw, CheckCircle, XCircle,
    AlertCircle, Search, Inbox
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const BADGE = {
    SAFE: {
        icon: <ShieldCheck className="w-4 h-4" />,
        label: '🟢 SAFE',
        bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    },
    SPAM: {
        icon: <AlertTriangle className="w-4 h-4" />,
        label: '🟡 SPAM',
        bg: 'bg-amber-50 text-amber-700 border-amber-200',
    },
    FRAUD: {
        icon: <ShieldX className="w-4 h-4" />,
        label: '🔴 FRAUD',
        bg: 'bg-red-50 text-red-700 border-red-200',
    },
};

const EmailSecurityDashboard = () => {
    const [email, setEmail] = useState('');
    const [maxResults, setMaxResults] = useState(20);
    const [isScanning, setIsScanning] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState('');
    const [expanded, setExpanded] = useState({});

    const handleScan = async () => {
        if (!email.trim()) {
            setError('Please enter a Gmail address to scan.');
            return;
        }
        setError('');
        setIsScanning(true);
        setResults(null);

        try {
            const resp = await fetch(
                `${API_URL}/api/email-security/scan?email=${encodeURIComponent(email)}&max_results=${maxResults}`
            );
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Scan failed.');
            setResults(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsScanning(false);
        }
    };

    const toggleExpand = (id) =>
        setExpanded(prev => ({ ...prev, [id]: !prev[id] }));

    const summary = results
        ? {
            total: results.scanned,
            safe: results.results.filter(r => r.classification === 'SAFE').length,
            spam: results.results.filter(r => r.classification === 'SPAM').length,
            fraud: results.results.filter(r => r.classification === 'FRAUD').length,
        }
        : null;

    return (
        <div className="min-h-screen bg-[#f8fbff] p-6 lg:p-10 font-sans mt-16 pb-20">

            {/* Header */}
            <div className="max-w-5xl mx-auto mb-10">
                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
                    <ShieldCheck className="w-10 h-10 text-indigo-600" />
                    AI Email Security Agent
                </h1>
                <p className="text-gray-500 mt-2 font-medium max-w-2xl">
                    Real-time inbox monitoring powered by VirusTotal + LLM analysis. Detects phishing, SPAM, and FRAUD, then automatically labels and quarantines threats.
                </p>
            </div>

            {/* Input Card */}
            <div className="max-w-5xl mx-auto mb-8">
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">
                    <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                        <Inbox className="w-4 h-4 text-indigo-500" /> Configure Scan
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="md:col-span-2">
                            <label className="block text-sm font-bold text-gray-700 mb-1.5">Gmail Address *</label>
                            <input
                                id="security-email-input"
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="e.g. you@gmail.com"
                                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none text-gray-700"
                            />
                            <p className="text-xs text-gray-400 mt-1">
                                Must have completed the Gmail OAuth flow via{' '}
                                <a href="/api/auth/google/url" target="_blank" className="text-indigo-500 underline" rel="noreferrer">
                                    Connect Gmail
                                </a>
                            </p>
                        </div>
                        <div>
                            <label className="block text-sm font-bold text-gray-700 mb-1.5">Emails to Scan</label>
                            <select
                                id="security-max-results"
                                value={maxResults}
                                onChange={e => setMaxResults(Number(e.target.value))}
                                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none text-gray-700"
                            >
                                {[5, 10, 20, 30, 50].map(n => (
                                    <option key={n} value={n}>{n} emails</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {error && (
                        <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 text-sm flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 shrink-0" /> {error}
                        </div>
                    )}

                    <div className="mt-6 flex justify-end">
                        <button
                            id="run-scan-btn"
                            onClick={handleScan}
                            disabled={isScanning}
                            className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold rounded-xl hover:from-indigo-700 hover:to-violet-700 transition-all shadow-lg shadow-indigo-200 flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                            {isScanning ? (
                                <><Loader2 className="w-5 h-5 animate-spin" /> Scanning Inbox...</>
                            ) : (
                                <><Search className="w-5 h-5" /> Run Security Scan</>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* Scanning indicator */}
            {isScanning && (
                <div className="max-w-5xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 p-12 flex flex-col items-center justify-center text-center">
                    <div className="relative mb-6">
                        <div className="w-20 h-20 rounded-full bg-indigo-100 flex items-center justify-center">
                            <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
                        </div>
                        <div className="absolute -inset-1 rounded-full border-2 border-indigo-200 animate-ping opacity-30" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Analyzing Your Inbox...</h3>
                    <p className="text-gray-500 max-w-md">
                        Running heuristic checks, VirusTotal attachment & link scans, and LLM analysis on each email. This may take up to a minute.
                    </p>
                </div>
            )}

            {/* Results */}
            {results && (
                <div className="max-w-5xl mx-auto space-y-6">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                            { label: 'Total Scanned', value: summary.total, color: 'text-gray-900', bg: 'bg-white' },
                            { label: 'Safe', value: summary.safe, color: 'text-emerald-700', bg: 'bg-emerald-50' },
                            { label: 'Spam', value: summary.spam, color: 'text-amber-700', bg: 'bg-amber-50' },
                            { label: 'Fraud', value: summary.fraud, color: 'text-red-700', bg: 'bg-red-50' },
                        ].map(card => (
                            <div key={card.label} className={`${card.bg} rounded-2xl border border-gray-100 p-5 shadow-sm`}>
                                <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">{card.label}</p>
                                <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
                            </div>
                        ))}
                    </div>

                    {/* Email Table */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
                            <Mail className="w-5 h-5 text-indigo-500" />
                            <h3 className="font-bold text-gray-900">Scan Results</h3>
                        </div>

                        <div className="divide-y divide-gray-50">
                            {results.results.map((item) => {
                                if (item.error) {
                                    return (
                                        <div key={item.email_id} className="px-6 py-4 flex items-center gap-3 text-sm text-red-600">
                                            <XCircle className="w-4 h-4" />
                                            <span className="font-mono text-xs">{item.email_id}</span>
                                            <span>— Error: {item.error}</span>
                                        </div>
                                    );
                                }

                                const badge = BADGE[item.classification] || BADGE.SAFE;
                                const isOpen = expanded[item.email_id];

                                return (
                                    <div key={item.email_id} className="px-6 py-4">
                                        <div
                                            className="flex items-start gap-3 cursor-pointer"
                                            onClick={() => toggleExpand(item.email_id)}
                                        >
                                            {/* Badge */}
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border ${badge.bg} shrink-0 mt-0.5`}>
                                                {badge.icon} {item.classification}
                                            </span>

                                            <div className="flex-1 min-w-0">
                                                <p className="font-semibold text-gray-900 truncate">{item.subject || '(No Subject)'}</p>
                                                <p className="text-xs text-gray-500 truncate mt-0.5">{item.sender}</p>
                                            </div>

                                            <div className="flex items-center gap-2 shrink-0">
                                                <span className={`text-xs px-2 py-0.5 rounded-full font-bold
                                                    ${item.confidence === 'high' ? 'bg-indigo-100 text-indigo-700' :
                                                        item.confidence === 'medium' ? 'bg-amber-100 text-amber-700' :
                                                            'bg-gray-100 text-gray-600'}`}>
                                                    {item.confidence} confidence
                                                </span>
                                                <RefreshCw className={`w-3.5 h-3.5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                                            </div>
                                        </div>

                                        {isOpen && (
                                            <div className="mt-3 pl-20 space-y-2">
                                                {item.reason && (
                                                    <p className="text-sm text-gray-700">
                                                        <span className="font-bold text-gray-500">Reason: </span>{item.reason}
                                                    </p>
                                                )}
                                                {item.heuristic_flags?.length > 0 && (
                                                    <div className="flex flex-wrap gap-1.5">
                                                        {item.heuristic_flags.map(f => (
                                                            <span key={f} className="text-xs bg-orange-50 text-orange-700 border border-orange-100 px-2 py-0.5 rounded-full font-mono">
                                                                {f}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                                {item.action_taken && (
                                                    <p className="text-xs text-gray-400">
                                                        <span className="font-bold">Action: </span>{item.action_taken}
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Re-scan button */}
                    <div className="flex justify-center">
                        <button
                            id="rescan-btn"
                            onClick={handleScan}
                            className="px-8 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-all shadow-md shadow-indigo-200 flex items-center gap-2"
                        >
                            <RefreshCw className="w-5 h-5" /> Scan Again
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EmailSecurityDashboard;
