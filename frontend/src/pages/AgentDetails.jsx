import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ChevronRight, Copy, Check, Download, MessageSquare, Shield, Zap, Play, X, Loader2 } from 'lucide-react';
import { agents } from '../data/agents';

const AgentDetails = () => {
    const { id } = useParams();
    const [agent, setAgent] = useState(null);
    const [pageTitle, setPageTitle] = useState('');
    const [copied, setCopied] = useState(false);

    // Modal & Execution State
    const [showRunModal, setShowRunModal] = useState(false);
    const [accessToken, setAccessToken] = useState('');
    const [isRunning, setIsRunning] = useState(false);
    const [executionResult, setExecutionResult] = useState(null);
    const [executionStatus, setExecutionStatus] = useState(null); // 'success', 'error'

    // Scheduler State
    const [isScheduled, setIsScheduled] = useState(false);
    const [scheduleType, setScheduleType] = useState('one-time'); // 'one-time', 'recurring'
    const [scheduleDate, setScheduleDate] = useState('');
    const [scheduleTime, setScheduleTime] = useState('');
    const [recurrence, setRecurrence] = useState('daily');

    useEffect(() => {
        let foundAgent = agents.find(a => a.id === id);
        if (!foundAgent && id) {
            foundAgent = agents.find(a =>
                a.title.toLowerCase().replace(/[^a-z0-9]+/g, '-') === id ||
                a.title === id
            );
        }
        if (foundAgent) {
            setAgent(foundAgent);
            setPageTitle(foundAgent.title);
        }
    }, [id]);

    const handleCopy = () => {
        navigator.clipboard.writeText(agent.prompt || "Default prompt text...");
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleRunAgent = async (e) => {
        e.preventDefault();
        setIsRunning(true);
        setExecutionResult(null);
        setExecutionStatus(null);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

            let endpoint = '/api/execute_agent';
            let body = {
                linkedin_access_token: accessToken,
                topic: agent.prompt
            };

            if (isScheduled) {
                endpoint = '/api/schedule_agent';
                body.schedule_type = scheduleType === 'one-time' ? 'date' : 'cron';
                body.schedule_params = {};

                if (scheduleType === 'one-time') {
                    if (!scheduleDate) throw new Error("Please select a date and time.");
                    // Convert to string that backend DateTrigger accepts (ISO)
                    body.schedule_params.run_date = new Date(scheduleDate).toISOString();
                } else {
                    if (!scheduleTime) throw new Error("Please select a time.");

                    const [hour, minute] = scheduleTime.split(':');
                    body.schedule_params.hour = hour;
                    body.schedule_params.minute = minute;

                    if (recurrence === 'weekly') {
                        body.schedule_params.day_of_week = 'mon'; // Defaulting to Monday for week start if not specified, or we could add day selector. 
                        // For simplicity let's stick to daily having no day param, weekly having a day. 
                        // Note: User asked for "daily weekly", implies just frequency.
                        // Ideally allow selecting day. For MVP user didn't specify interaction depth.
                        // I will implicitly run "every week on this day" based on today, or just Monday.
                        // Let's keep it simple: "daily" implies * * * * *, "weekly" implies * * * * mon.
                        // Better: just pass cron args.
                        // If weekly, we need to know WHICH day. I'll default to MONDAY for now to avoid UI clutter unless I add a day selector.
                        // Actually, let's just use 'daily' for now as the 'recurring' implementation example, or add a simple day selector.
                        // I'll add day selector if 'weekly' is picked.
                    }
                }
            }

            const response = await fetch(`${apiUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(body),
            });

            const data = await response.json();

            if (response.ok) {
                setExecutionResult(data);
                setExecutionStatus('success');
            } else {
                setExecutionResult({ error: data.detail || 'Failed to request agent' });
                setExecutionStatus('error');
            }
        } catch (error) {
            setExecutionResult({ error: error.message });
            setExecutionStatus('error');
        } finally {
            setIsRunning(false);
        }
    };

    if (!agent) {
        return (
            <div className="min-h-screen pt-24 text-center">
                <p>Loading agent details...</p>
                <Link to="/search" className="text-blue-600 hover:underline">Return to Search</Link>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#f8fbff] pt-24 pb-20">
            <div className="container mx-auto px-6 max-w-7xl">

                {/* Breadcrumbs */}
                <div className="mb-8">
                    <Link to="/search" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-blue-600 mb-4 transition-colors">
                        <ArrowLeft className="w-4 h-4" /> Back
                    </Link>
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                        <Link to="/" className="hover:text-blue-600">Home</Link>
                        <ChevronRight className="w-3 h-3" />
                        <Link to="/search" className="hover:text-blue-600">Marketplace</Link>
                        <ChevronRight className="w-3 h-3" />
                        <span className="text-gray-400">Search</span>
                        <ChevronRight className="w-3 h-3" />
                        <span className="text-gray-900 font-medium">{agent.title}</span>
                    </div>
                </div>

                {/* Main Content Card */}
                <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="p-8 lg:p-12 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">

                        {/* Left Column: Details */}
                        <div className="space-y-8">
                            <div>
                                <h1 className="text-4xl font-bold text-gray-900 mb-2">{agent.title}</h1>
                                <span className="text-blue-600 font-medium bg-blue-50 px-3 py-1 rounded-full text-sm">
                                    {agent.agentType || 'Prompt Agent'}
                                </span>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-2">Description</h3>
                                <p className="text-gray-600 leading-relaxed text-lg">
                                    {agent.description}
                                </p>
                            </div>

                            <div className="flex flex-wrap gap-y-4 gap-x-8">
                                <div>
                                    <span className="text-sm text-gray-500 block mb-1">Categories :</span>
                                    <div className="flex gap-2">
                                        {agent.tags && agent.tags.map(tag => (
                                            <span key={tag} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm font-medium border border-gray-200">
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div>
                                    <span className="text-sm text-gray-500 block mb-1">Works With :</span>
                                    <div className="flex flex-wrap gap-2 text-sm">
                                        {agent.integrations && agent.integrations.length > 0 ? (
                                            agent.integrations.map((integration, idx) => (
                                                <div key={idx} className="flex items-center gap-2 px-2 py-1 bg-white border border-gray-100 rounded shadow-sm">
                                                    <span className="text-gray-700 font-medium capitalize">{integration}</span>
                                                </div>
                                            ))
                                        ) : (
                                            <div className="flex items-center gap-2">
                                                <div className="w-6 h-6 bg-green-100 text-green-700 rounded flex items-center justify-center text-xs font-bold">O</div>
                                                <span className="text-gray-700 font-medium">OpenAI GPT-4o</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div>
                                <span className="text-sm text-gray-500 block mb-1">Teams:</span>
                                <span className="inline-block px-3 py-1 border border-gray-200 rounded-md text-gray-700 text-sm font-medium">
                                    {agent.industry || 'All teams'}
                                </span>
                            </div>

                            <div className="flex gap-4 pt-4">
                                {agent.id === 'sec-1' ? (
                                    <button
                                        onClick={() => setShowRunModal(true)}
                                        className="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-lg shadow-blue-200 hover:shadow-xl transition-all active:scale-95 flex items-center gap-2"
                                    >
                                        <Play className="w-5 h-5" /> Run Agent
                                    </button>
                                ) : (
                                    <button className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700 hover:shadow-xl transition-all active:scale-95">
                                        Install
                                    </button>
                                )}

                                <button className="px-8 py-3 bg-white text-gray-700 font-semibold rounded-xl border border-gray-200 hover:bg-gray-50 hover:border-gray-300 transition-all active:scale-95">
                                    Contact Sales
                                </button>
                            </div>
                        </div>

                        {/* Right Column: Visual */}
                        <div className="relative">
                            <div className="aspect-[4/3] bg-gradient-to-br from-blue-50 to-indigo-50 rounded-3xl border border-blue-100 flex items-center justify-center relative overflow-hidden group">
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="w-[80%] h-[80%] border border-blue-100 rounded-full animate-pulse-slow"></div>
                                    <div className="w-[60%] h-[60%] border border-blue-200 rounded-full absolute"></div>
                                    <div className="w-[40%] h-[40%] border border-blue-300 rounded-full absolute"></div>
                                </div>
                                <div className="bg-white p-6 rounded-2xl shadow-xl relative z-10 flex items-center gap-4 animate-float">
                                    <div className="w-12 h-12 bg-black rounded-full flex items-center justify-center">
                                        <div className="w-6 h-6 border-2 border-white rounded-full border-t-transparent animate-spin"></div>
                                    </div>
                                    <span className="font-semibold text-gray-900">Agent Marketplace</span>
                                </div>
                            </div>
                        </div>

                    </div>

                    {/* Prompt Section */}
                    <div className="bg-gray-50 border-t border-gray-100 p-8 lg:p-12">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-gray-900">Prompt</h3>
                            <button
                                onClick={handleCopy}
                                className="flex items-center gap-2 text-sm text-blue-600 font-medium hover:bg-blue-50 px-3 py-1.5 rounded-lg transition-colors"
                            >
                                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                {copied ? 'Copied' : 'Copy'}
                            </button>
                        </div>
                        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                            <p className="text-gray-600 leading-relaxed font-mono text-sm">
                                {agent.prompt || `Default agent prompt...`}
                            </p>
                        </div>
                    </div>

                </div>
            </div>

            {/* Run Agent Modal */}
            <AnimatePresence>
                {showRunModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
                        onClick={() => setShowRunModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
                            onClick={e => e.stopPropagation()}
                        >
                            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                                <h2 className="text-xl font-bold text-gray-900">Run {agent.title}</h2>
                                <button onClick={() => setShowRunModal(false)} className="text-gray-400 hover:text-gray-600">
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            <div className="p-6">
                                {!executionResult && !isRunning && (
                                    <form onSubmit={handleRunAgent} className="space-y-4">
                                        <div className="p-4 bg-blue-50 rounded-xl text-sm text-blue-700 mb-4">
                                            This agent will search specifically for news from <strong>Google, GPT, and Linux Foundation</strong> regarding Cybersecurity and post it to your <strong>LinkedIn</strong>.
                                        </div>

                                        <div className="mb-4">
                                            <label className="block text-gray-400 text-sm font-bold mb-2">
                                                LinkedIn Access Token
                                            </label>
                                            <textarea
                                                className="shadow appearance-none border border-gray-700 bg-gray-900 rounded w-full py-2 px-3 text-gray-300 leading-tight focus:outline-none focus:shadow-outline"
                                                rows="3"
                                                placeholder="Paste your OAuth Access Token here..."
                                                value={accessToken}
                                                onChange={(e) => setAccessToken(e.target.value)}
                                                required
                                            />
                                            {/* <p className="text-xs text-gray-500 mt-1">
                            Run 'generate_token.py' locally to generate this token.
                        </p> */}
                                        </div>

                                        <div className="border-t border-gray-100 pt-4 mb-4">
                                            <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 cursor-pointer select-none">
                                                <input
                                                    type="checkbox"
                                                    checked={isScheduled}
                                                    onChange={(e) => setIsScheduled(e.target.checked)}
                                                    className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                                                />
                                                Schedule this task
                                            </label>

                                            <AnimatePresence>
                                                {isScheduled && (
                                                    <motion.div
                                                        initial={{ height: 0, opacity: 0 }}
                                                        animate={{ height: 'auto', opacity: 1 }}
                                                        exit={{ height: 0, opacity: 0 }}
                                                        className="overflow-hidden mt-3"
                                                    >
                                                        <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-4">
                                                            <div>
                                                                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5">Schedule Type</label>
                                                                <select
                                                                    value={scheduleType}
                                                                    onChange={(e) => setScheduleType(e.target.value)}
                                                                    className="w-full text-sm border-gray-300 rounded-lg shadow-sm text-gray-700 focus:border-blue-500 focus:ring-blue-500"
                                                                >
                                                                    <option value="one-time">One Time (Specific Date)</option>
                                                                    <option value="recurring">Recurring (Daily/Weekly)</option>
                                                                </select>
                                                            </div>

                                                            {scheduleType === 'one-time' && (
                                                                <div>
                                                                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5">Run At</label>
                                                                    <input
                                                                        type="datetime-local"
                                                                        value={scheduleDate}
                                                                        onChange={(e) => setScheduleDate(e.target.value)}
                                                                        className="w-full text-sm border-gray-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                                                    />
                                                                </div>
                                                            )}

                                                            {scheduleType === 'recurring' && (
                                                                <div className="grid grid-cols-2 gap-3">
                                                                    <div>
                                                                        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5">Frequency</label>
                                                                        <select
                                                                            value={recurrence}
                                                                            onChange={(e) => setRecurrence(e.target.value)}
                                                                            className="w-full text-sm border-gray-300 rounded-lg shadow-sm text-gray-700 focus:border-blue-500 focus:ring-blue-500"
                                                                        >
                                                                            <option value="daily">Daily</option>
                                                                            <option value="weekly">Weekly</option>
                                                                        </select>
                                                                    </div>
                                                                    <div>
                                                                        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5">Time</label>
                                                                        <input
                                                                            type="time"
                                                                            value={scheduleTime}
                                                                            onChange={(e) => setScheduleTime(e.target.value)}
                                                                            className="w-full text-sm border-gray-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                                                        />
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </motion.div>
                                                )}
                                            </AnimatePresence>
                                        </div>

                                        <div className="pt-4">
                                            <button
                                                type="submit"
                                                className="w-full py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 transition-colors shadow-lg shadow-blue-200"
                                            >
                                                {isScheduled ? 'Schedule Task' : 'Run Agent Now'}
                                            </button>
                                        </div>
                                    </form>
                                )}

                                {isRunning && (
                                    <div className="py-12 flex flex-col items-center justify-center text-center">
                                        <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
                                        <h3 className="text-lg font-semibold text-gray-900">Agent is running...</h3>
                                        <p className="text-gray-500">Searching web, generating content, and connecting to LinkedIn.</p>
                                    </div>
                                )}

                                {executionResult && (
                                    <div className="space-y-4">
                                        {executionStatus === 'success' ? (
                                            <div className="p-4 bg-green-50 text-green-700 rounded-xl border border-green-100 flex items-start gap-3">
                                                <Check className="w-5 h-5 mt-0.5 shrink-0" />
                                                <div>
                                                    <p className="font-bold">Success!</p>
                                                    <p className="text-sm">{executionResult.status}</p>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
                                                <p className="font-bold">Error</p>
                                                <p className="text-sm">{executionResult.error}</p>
                                            </div>
                                        )}

                                        {executionResult.newsletter && (
                                            <div className="mt-4">
                                                <h4 className="font-semibold text-gray-900 mb-2">Generated Newsletter:</h4>
                                                <div className="bg-gray-50 p-4 rounded-xl text-sm text-gray-700 whitespace-pre-wrap max-h-60 overflow-y-auto border border-gray-200">
                                                    {executionResult.newsletter}
                                                </div>
                                            </div>
                                        )}

                                        <button
                                            onClick={() => { setExecutionResult(null); setIsRunning(false); }}
                                            className="w-full mt-4 py-2 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition-colors"
                                        >
                                            Run Again
                                        </button>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const ChevronDown = ({ className }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="m6 9 6 6 6-6" /></svg>
);

export default AgentDetails;
