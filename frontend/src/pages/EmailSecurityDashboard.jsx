import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    ShieldCheck, ShieldAlert, ShieldX, Mail, Link as LinkIcon,
    Loader2, AlertTriangle, RefreshCw, CheckCircle, XCircle,
    AlertCircle, Search, Inbox, LogIn, ExternalLink, Wifi
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/* ── Classification badges ─────────────────────────────────────────────── */
const BADGE = {
    SAFE: { icon: <ShieldCheck className="w-4 h-4" />, label: '🟢 SAFE', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    SUSPICIOUS: { icon: <AlertCircle className="w-4 h-4" />, label: '🟠 SUSPICIOUS', bg: 'bg-orange-50 text-orange-700 border-orange-200' },
    SPAM: { icon: <AlertTriangle className="w-4 h-4" />, label: '🟡 SPAM', bg: 'bg-amber-50 text-amber-700 border-amber-200' },
    FRAUD: { icon: <ShieldX className="w-4 h-4" />, label: '🔴 FRAUD', bg: 'bg-red-50 text-red-700 border-red-200' },
};

/* ── Trust level colour ────────────────────────────────────────────────── */
const TRUST_COLOR = {
    HIGH_TRUST: 'bg-emerald-100 text-emerald-700',
    MEDIUM_TRUST: 'bg-amber-100 text-amber-700',
    LOW_TRUST: 'bg-red-100 text-red-700',
    UNKNOWN: 'bg-gray-100 text-gray-500',
};

/* ═══════════════════════════════════════════════════════════════════════════
   Main Component
═══════════════════════════════════════════════════════════════════════════ */
const EmailSecurityDashboard = () => {
    const { currentUser } = useAuth();
    const [searchParams] = useSearchParams();
    const justConnected = searchParams.get('connected') === 'true';

    const [gmailConnected, setGmailConnected] = useState(false);
    const [checkingConnection, setCheckingConnection] = useState(true);
    const [connectLoading, setConnectLoading] = useState(false);

    const [maxResults, setMaxResults] = useState(10);
    const [isScanning, setIsScanning] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState('');
    const [expanded, setExpanded] = useState({});

    // Derive email directly from Firebase user
    const email = currentUser?.email || '';

    /* ── Check if Gmail already connected on mount ─────────────────────── */
    useEffect(() => {
        if (!email) {
            setCheckingConnection(false);
            return;
        }
        (async () => {
            try {
                const resp = await fetch(`${API_URL}/api/auth/gmail/connected?email=${encodeURIComponent(email)}`);
                const data = await resp.json();
                setGmailConnected(data.connected);
            } catch {
                setGmailConnected(false);
            } finally {
                setCheckingConnection(false);
            }
        })();
    }, [email]);

    // If user just came back from OAuth consent, mark as connected
    useEffect(() => {
        if (justConnected) setGmailConnected(true);
    }, [justConnected]);

    /* ── Open Google OAuth consent ─────────────────────────────────────── */
    const handleConnectGmail = async () => {
        setConnectLoading(true);
        setError('');
        try {
            const resp = await fetch(`${API_URL}/api/auth/gmail/connect`);
            const data = await resp.json();
            if (data.url) {
                window.location.href = data.url;
            } else {
                setError('Could not get Google OAuth URL. Check backend configuration.');
                setConnectLoading(false);
            }
        } catch (err) {
            setError('Failed to start Gmail connection: ' + err.message);
            setConnectLoading(false);
        }
    };

    /* ── Run scan ──────────────────────────────────────────────────────── */
    const handleScan = async () => {
        if (!email) return;
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

    const toggleExpand = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }));

    const summary = results ? {
        total: results.scanned,
        safe: results.results.filter(r => r.classification === 'SAFE').length,
        suspicious: results.results.filter(r => r.classification === 'SUSPICIOUS').length,
        spam: results.results.filter(r => r.classification === 'SPAM').length,
        fraud: results.results.filter(r => r.classification === 'FRAUD').length,
    } : null;

    /* ════════════════════ RENDER ════════════════════════════════════════ */
    return (
        <div className="min-h-screen bg-[#f8fbff] p-6 lg:p-10 font-sans mt-16 pb-20">

            {/* Header */}
            <div className="max-w-5xl mx-auto mb-8">
                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
                    <ShieldCheck className="w-10 h-10 text-indigo-600" />
                    AI Email Security Agent
                </h1>
                <p className="text-gray-500 mt-2 font-medium max-w-2xl">
                    Real-time inbox monitoring powered by VirusTotal + LLM. Detects phishing, SPAM, and FRAUD.
                </p>
            </div>

            {/* ── Connected Success Banner ── */}
            {justConnected && (
                <div className="max-w-5xl mx-auto mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-3 text-emerald-700 font-semibold shadow-sm">
                    <CheckCircle className="w-5 h-5 shrink-0" />
                    Gmail successfully connected! Your inbox is now ready to scan.
                </div>
            )}

            {/* ── Gmail OAuth Connect Card ── */}
            {!checkingConnection && !gmailConnected && (
                <div className="max-w-5xl mx-auto mb-6">
                    <div className="bg-white rounded-2xl border-2 border-dashed border-indigo-200 p-8 flex flex-col md:flex-row items-center gap-6 shadow-sm">
                        <div className="w-16 h-16 rounded-2xl bg-indigo-100 flex items-center justify-center shrink-0">
                            <Mail className="w-8 h-8 text-indigo-600" />
                        </div>
                        <div className="flex-1 text-center md:text-left">
                            <h3 className="text-lg font-bold text-gray-900 mb-1">Connect Your Gmail Account</h3>
                            <p className="text-sm text-gray-500">
                                To analyze your inbox, grant the agent read access to your Gmail.
                                This is a one-time step. Your OAuth tokens are stored securely in our database.
                            </p>
                            <p className="text-xs text-gray-400 mt-1">
                                Logged in as <span className="font-semibold text-indigo-600">{email}</span>
                            </p>
                        </div>
                        <button
                            onClick={handleConnectGmail}
                            disabled={connectLoading}
                            className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold rounded-xl hover:from-indigo-700 hover:to-violet-700 transition-all shadow-lg shadow-indigo-200 flex items-center gap-2 disabled:opacity-70 shrink-0"
                        >
                            {connectLoading ? (
                                <><Loader2 className="w-5 h-5 animate-spin" /> Connecting...</>
                            ) : (
                                <><LogIn className="w-5 h-5" /> Connect Gmail</>
                            )}
                        </button>
                    </div>
                </div>
            )}

            {/* ── Gmail Connected indicator + Scan Config ── */}
            {!checkingConnection && gmailConnected && (
                <div className="max-w-5xl mx-auto mb-8">
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">

                        {/* Connected status bar */}
                        <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
                            <div className="flex items-center gap-2 text-sm">
                                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                <span className="text-gray-600 font-medium">
                                    Gmail connected as <span className="font-bold text-gray-900">{email}</span>
                                </span>
                            </div>
                            <button
                                onClick={handleConnectGmail}
                                className="text-xs text-indigo-500 hover:underline flex items-center gap-1"
                            >
                                <RefreshCw className="w-3 h-3" /> Reconnect
                            </button>
                        </div>

                        <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                            <Inbox className="w-4 h-4 text-indigo-500" /> Configure Scan
                        </h3>

                        <div className="flex flex-col sm:flex-row gap-4 items-end">
                            <div className="flex-1">
                                <label className="block text-sm font-bold text-gray-700 mb-1.5">
                                    Emails to Analyze (newest unread, unlabeled)
                                </label>
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
                                <p className="text-xs text-gray-400 mt-1">
                                    Already-labeled emails are automatically skipped.
                                </p>
                            </div>
                            <button
                                id="run-scan-btn"
                                onClick={handleScan}
                                disabled={isScanning}
                                className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold rounded-xl hover:from-indigo-700 hover:to-violet-700 transition-all shadow-lg shadow-indigo-200 flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {isScanning ? (
                                    <><Loader2 className="w-5 h-5 animate-spin" /> Scanning...</>
                                ) : (
                                    <><Search className="w-5 h-5" /> Run Security Scan</>
                                )}
                            </button>
                        </div>

                        {error && (
                            <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 text-sm flex items-center gap-2">
                                <AlertCircle className="w-5 h-5 shrink-0" /> {error}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ── Scanning animation ── */}
            {isScanning && (
                <div className="max-w-5xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 p-12 flex flex-col items-center text-center">
                    <div className="relative mb-6">
                        <div className="w-20 h-20 rounded-full bg-indigo-100 flex items-center justify-center">
                            <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
                        </div>
                        <div className="absolute -inset-1 rounded-full border-2 border-indigo-200 animate-ping opacity-30" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Analyzing Your Inbox...</h3>
                    <p className="text-gray-500 max-w-md">
                        Running domain trust checks, VirusTotal scans, and LLM analysis on new emails.
                        This may take up to a minute.
                    </p>
                </div>
            )}

            {/* ── Results ── */}
            {results && (
                <div className="max-w-5xl mx-auto space-y-6">

                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        {[
                            { label: 'Total Scanned', value: summary.total, color: 'text-gray-900', bg: 'bg-white' },
                            { label: 'Safe', value: summary.safe, color: 'text-emerald-700', bg: 'bg-emerald-50' },
                            { label: 'Suspicious', value: summary.suspicious, color: 'text-orange-700', bg: 'bg-orange-50' },
                            { label: 'Spam', value: summary.spam, color: 'text-amber-700', bg: 'bg-amber-50' },
                            { label: 'Fraud', value: summary.fraud, color: 'text-red-700', bg: 'bg-red-50' },
                        ].map(card => (
                            <div key={card.label} className={`${card.bg} rounded-2xl border border-gray-100 p-5 shadow-sm`}>
                                <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">{card.label}</p>
                                <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
                            </div>
                        ))}
                    </div>

                    {/* No new emails state */}
                    {summary.total === 0 && (
                        <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center shadow-sm">
                            <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                            <h3 className="font-bold text-gray-800 text-lg mb-1">All Clear!</h3>
                            <p className="text-gray-500 text-sm">No new unanalyzed emails found. New emails will be scanned automatically when they arrive.</p>
                        </div>
                    )}

                    {/* Email Table */}
                    {summary.total > 0 && (
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
                                    const trustClass = TRUST_COLOR[item.trust_level] || TRUST_COLOR.UNKNOWN;

                                    return (
                                        <div key={item.email_id} className="px-6 py-4">
                                            <div
                                                className="flex items-start gap-3 cursor-pointer"
                                                onClick={() => toggleExpand(item.email_id)}
                                            >
                                                {/* Classification Badge */}
                                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border ${badge.bg} shrink-0 mt-0.5`}>
                                                    {badge.icon} {item.classification}
                                                </span>

                                                <div className="flex-1 min-w-0">
                                                    <p className="font-semibold text-gray-900 truncate">{item.subject || '(No Subject)'}</p>
                                                    <p className="text-xs text-gray-500 truncate mt-0.5">{item.sender}</p>
                                                </div>

                                                <div className="flex items-center gap-2 shrink-0">
                                                    {/* Trust level */}
                                                    {item.trust_level && (
                                                        <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${trustClass}`}>
                                                            {item.trust_level?.replace('_', ' ')}
                                                        </span>
                                                    )}
                                                    {/* Confidence */}
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
                    )}

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
