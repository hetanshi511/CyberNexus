import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ChevronRight, Copy, Check, Download, MessageSquare, Shield, Zap, Play, X, Loader2, FileText } from 'lucide-react';
import { agents } from '../data/agents';
import { useAuth } from '../context/AuthContext';
import HeaderValidatorReport from '../components/HeaderValidatorReport';

const AgentDetails = () => {
    const { id } = useParams();
    const [agent, setAgent] = useState(null);
    const [pageTitle, setPageTitle] = useState('');
    const [copied, setCopied] = useState(false);
    const { currentUser, getIdToken } = useAuth();
    const navigate = useNavigate();

    // Modal & Execution State
    const [showRunModal, setShowRunModal] = useState(false);
    const [accessToken, setAccessToken] = useState('');
    const [policySource, setPolicySource] = useState('');
    const [policyTarget, setPolicyTarget] = useState('');
    const [vendorName, setVendorName] = useState('');
    const [vendorDocs, setVendorDocs] = useState('');
    const [websiteUrl, setWebsiteUrl] = useState('');
    const [maxPages, setMaxPages] = useState(5);
    const [maxDepth, setMaxDepth] = useState(2);
    const [sendToEmail, setSendToEmail] = useState(false);
    const [reportEmail, setReportEmail] = useState('');
    // Jira State
    const [jiraProjectKey, setJiraProjectKey] = useState('');
    const [jiraTicketId, setJiraTicketId] = useState('');
    const [jiraDomain, setJiraDomain] = useState('');
    const [jiraEmail, setJiraEmail] = useState('');
    const [jiraToken, setJiraToken] = useState('');

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

    const handleTestRun = async (e) => {
        e.preventDefault();
        setIsRunning(true);
        setExecutionResult(null);
        setExecutionStatus(null);
        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const idToken = await getIdToken();
            const response = await fetch(`${apiUrl}/api/compliance/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`,
                },
                body: JSON.stringify({ count: testCount }),
            });
            const data = await response.json();
            if (response.ok) {
                setExecutionResult(data);
                setExecutionStatus('success');
            } else {
                setExecutionResult({ error: data.detail || 'Test run failed' });
                setExecutionStatus('error');
            }
        } catch (error) {
            setExecutionResult({ error: error.message });
            setExecutionStatus('error');
        } finally {
            setIsRunning(false);
        }
    };

    const handleRunAgent = async (e) => {
        e.preventDefault();
        setIsRunning(true);
        setExecutionResult(null);
        setExecutionStatus(null);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const idToken = await getIdToken();

            let endpoint = '/api/execute_agent';
            let body = {
                agent_id: agent.id,
                linkedin_access_token: accessToken,
                topic: agent.prompt,
                policy_source: policySource,
                policy_target: policyTarget,
                vendor_name: vendorName,
                vendor_docs: vendorDocs,
                website_url: websiteUrl,
                max_pages: parseInt(maxPages, 10) || 5,
                max_depth: parseInt(maxDepth, 10) || 2,
                send_email_to: sendToEmail ? reportEmail : null,
                jira_project_key: jiraProjectKey,
                jira_ticket_id: jiraTicketId,
                jira_domain: jiraDomain,
                jira_email: jiraEmail,
                jira_token: jiraToken
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
                    'Authorization': `Bearer ${idToken}`,
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
                                {currentUser ? (
                                    <button
                                        onClick={() => {
                                            if (agent.id === 'resume-reviewer') {
                                                navigate('/resume-reviewer-dashboard');
                                            } else if (agent.id === 'scheduler-agent') {
                                                navigate('/scheduler-dashboard');
                                            } else if (agent.id === 'email-security') {
                                                navigate('/email-security-dashboard');
                                            } else if (agent.id === 'ppt-generator') {
                                                navigate('/ppt-generator-dashboard');
                                            } else if (agent.id === 'ppt-db-generator') {
                                                navigate('/ppt-db-generator-dashboard');
                                            } else {
                                                setShowRunModal(true);
                                            }
                                        }}
                                        className="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-lg shadow-blue-200 hover:shadow-xl transition-all active:scale-95 flex items-center gap-2"
                                    >
                                        <Play className="w-5 h-5" /> Run Agent
                                    </button>
                                ) : (
                                    <div className="flex flex-col gap-2">
                                        <Link
                                            to="/login"
                                            className="px-8 py-3 bg-gray-900 text-white font-semibold rounded-xl shadow-lg hover:bg-gray-800 transition-all active:scale-95 flex items-center gap-2 justify-center"
                                        >
                                            Login to Run Agent
                                        </Link>
                                        <p className="text-xs text-gray-500 text-center">Authentication required</p>
                                    </div>
                                )}
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

                                        {agent.id === 'compliance-bot' ? (
                                            <>
                                                <div className="p-4 bg-green-50 rounded-xl text-sm text-green-700 mb-4">
                                                    This agent will fetch and analyze a Jira ticket for compliance alignment.
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Jira Project Key (e.g. PROJ)
                                                    </label>
                                                    <input
                                                        type="text"
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-green-500"
                                                        placeholder="PROJ"
                                                        value={jiraProjectKey}
                                                        onChange={(e) => setJiraProjectKey(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Jira Domain (e.g. your-company.atlassian.net)
                                                    </label>
                                                    <input
                                                        type="text"
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-green-500"
                                                        placeholder="your-company.atlassian.net"
                                                        value={jiraDomain}
                                                        onChange={(e) => setJiraDomain(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Jira Email
                                                    </label>
                                                    <input
                                                        type="email"
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-green-500"
                                                        placeholder="user@example.com"
                                                        value={jiraEmail}
                                                        onChange={(e) => setJiraEmail(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Jira API Token
                                                    </label>
                                                    <input
                                                        type="password"
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-green-500"
                                                        placeholder="API Token"
                                                        value={jiraToken}
                                                        onChange={(e) => setJiraToken(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                            </>
                                        ) : agent.id === 'sec-2' ? (
                                            <>
                                                <div className="p-4 bg-purple-50 rounded-xl text-sm text-purple-700 mb-4">
                                                    This agent will compare two policy documents and highlight conflicts.
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Source Policy (e.g. Internal Draft)
                                                    </label>
                                                    <textarea
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-purple-500"
                                                        rows="4"
                                                        placeholder="Paste your internal policy text here..."
                                                        value={policySource}
                                                        onChange={(e) => setPolicySource(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Target Standard (e.g. ISO 27001 / GDPR)
                                                    </label>
                                                    <textarea
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-purple-500"
                                                        rows="4"
                                                        placeholder="Paste the standard text or reference policy here..."
                                                        value={policyTarget}
                                                        onChange={(e) => setPolicyTarget(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                            </>
                                        ) : agent.id === 'sec-3' ? (
                                            <>
                                                <div className="p-4 bg-orange-50 rounded-xl text-sm text-orange-700 mb-4">
                                                    This agent will analyze vendor documentation to assess security risks.
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Vendor Name
                                                    </label>
                                                    <input
                                                        type="text"
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-orange-500"
                                                        placeholder="e.g. Acme Corp"
                                                        value={vendorName}
                                                        onChange={(e) => setVendorName(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Security Documentation / Claims
                                                    </label>
                                                    <textarea
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-orange-500"
                                                        rows="5"
                                                        placeholder="Paste the vendor's security page content, certifications, or compliance summary here..."
                                                        value={vendorDocs}
                                                        onChange={(e) => setVendorDocs(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                            </>
                                        ) : agent.id === 'content-reviewer' ? (
                                            <>
                                                <div className="p-4 bg-teal-50 rounded-xl text-sm text-teal-700 mb-4">
                                                    This agent will crawl a website and review the content for typos, grammar, and punctuation errors.
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Website URL
                                                    </label>
                                                    <input
                                                        type="url"
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-teal-500"
                                                        placeholder="https://example.com"
                                                        value={websiteUrl}
                                                        onChange={(e) => setWebsiteUrl(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                                <div className="grid grid-cols-2 gap-4 mb-4">
                                                    <div>
                                                        <label className="block text-gray-700 text-sm font-bold mb-2">Max Pages</label>
                                                        <input
                                                            type="number"
                                                            min="1"
                                                            max="50"
                                                            className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-teal-500"
                                                            value={maxPages}
                                                            onChange={(e) => setMaxPages(e.target.value)}
                                                            required
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-gray-700 text-sm font-bold mb-2">Max Depth</label>
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            max="10"
                                                            className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-teal-500"
                                                            value={maxDepth}
                                                            onChange={(e) => setMaxDepth(e.target.value)}
                                                            required
                                                        />
                                                    </div>
                                                </div>
                                            </>
                                        ) : agent.id === 'header-validator' ? (
                                            <>
                                                <div className="p-4 bg-blue-50 rounded-xl text-sm text-blue-700 mb-4">
                                                    This agent will perform a deep security analysis of a site's HTTP headers.
                                                </div>
                                                <div className="mb-4">
                                                    <label className="block text-gray-700 text-sm font-bold mb-2">
                                                        Website URL
                                                    </label>
                                                    <input
                                                        type="url"
                                                        className="shadow appearance-none border border-gray-300 rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                        placeholder="https://example.com"
                                                        value={websiteUrl}
                                                        onChange={(e) => setWebsiteUrl(e.target.value)}
                                                        required
                                                    />
                                                </div>
                                            </>
                                        ) : (
                                            <>
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
                                                </div>
                                            </>
                                        )}




                                        {agent.id !== 'compliance-bot' && agent.id !== 'content-reviewer' && agent.id !== 'header-validator' && (
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
                                        )}

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
                                        <p className="text-gray-500">
                                            {agent.id === 'compliance-bot' 
                                                ? 'Connecting to JIRA and fetching, analyzing the tickets...' 
                                                : agent.id === 'content-reviewer'
                                                    ? 'Scraping and analyzing the web page...'
                                                    : agent.id === 'header-validator'
                                                        ? 'Analyzing site security headers...'
                                                    : 'Searching web, generating content, and connecting to LinkedIn.'}
                                        </p>
                                    </div>
                                )}

                                {executionResult && (
                                    <div className="space-y-4">
                                        {(() => {
                                            const status = executionResult?.status?.toLowerCase() || '';
                                            const analysisStatus = executionResult?.analysis_result?.status?.toLowerCase() || '';
                                            const isFailure = status.includes('failed') || status.includes('error') || analysisStatus.includes('error') || analysisStatus.includes('failed');
                                            
                                            return (executionStatus === 'success' && !isFailure) ? (
                                                <div className="p-4 bg-green-50 text-green-700 rounded-xl border border-green-100 flex items-start gap-3">
                                                    <Check className="w-5 h-5 mt-0.5 shrink-0" />
                                                    <div>
                                                        <p className="font-bold">Success!</p>
                                                        <p className="text-sm">{executionResult.status}</p>
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
                                                    <p className="font-bold">Execution Warning / Error</p>
                                                    <p className="text-sm">{executionResult?.error || executionResult?.status || 'An error occurred during analysis.'}</p>
                                                    {executionResult?.analysis_result?.details && (
                                                        <p className="text-xs mt-1 font-mono bg-red-100 p-1 rounded">{executionResult.analysis_result.details}</p>
                                                    )}
                                                </div>
                                            );
                                        })()}

                                        {(executionResult.newsletter || executionResult.report || executionResult.analysis_result) && (
                                            <div className="mt-4">
                                                <h4 className="font-semibold text-gray-900 mb-2">
                                                    {agent.id === 'content-reviewer' && executionResult.report?.pages
                                                        ? 'Content Review Summary:'
                                                        : agent.id === 'header-validator' && executionResult.report
                                                            ? ''
                                                        : executionResult.newsletter 
                                                            ? 'Generated Newsletter:' 
                                                            : executionResult.analysis_result 
                                                                ? 'Compliance Project Report:'
                                                                : 'Conflict Analysis Report:'}
                                                </h4>
                                                
                                                {/* Table View for Compliance Agent */}
                                                {executionResult.analysis_result && Array.isArray(executionResult.analysis_result) ? (
                                                    <div className="space-y-3">
                                                        <div className="flex justify-end">
                                                            <button
                                                                onClick={() => {
                                                                    localStorage.setItem('latest_compliance_report', JSON.stringify(executionResult.analysis_result));
                                                                    window.open('/compliance-dashboard', '_blank');
                                                                }}
                                                                className="px-4 py-2 bg-blue-50 text-blue-700 text-sm font-semibold rounded-lg hover:bg-blue-100 transition-colors flex items-center gap-2"
                                                            >
                                                                View Full Report ↗
                                                            </button>
                                                        </div>
                                                        <div className="overflow-x-auto border border-gray-200 rounded-xl max-h-[600px]">
                                                        <table className="min-w-full divide-y divide-gray-200 relative">
                                                            <thead className="bg-gray-50 sticky top-0 z-10 shadow-sm">
                                                                <tr>
                                                                    <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap">Ticket</th>
                                                                    <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider min-w-[300px]">Summary</th>
                                                                    <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap">Status</th>
                                                                    <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap">Alignment</th>
                                                                    <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap">Comp %</th>
                                                                    <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap">Risk</th>
                                                                    <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider min-w-[250px]">Action</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody className="bg-white divide-y divide-gray-200">
                                                                {executionResult.analysis_result.map((row, idx) => (
                                                                    <tr key={idx} className={`hover:bg-gray-50 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`}>
                                                                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-blue-600 align-top">
                                                                            <a href={`https://${jiraDomain}/browse/${row.key}`} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1">
                                                                                {row.key} <span className="text-xs text-gray-400">↗</span>
                                                                            </a>
                                                                        </td>
                                                                        <td className="px-4 py-4 text-sm text-gray-800 align-top leading-relaxed">
                                                                            {row.summary}
                                                                        </td>
                                                                        <td className="px-4 py-4 whitespace-nowrap text-xs align-top">
                                                                            <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                                                row.status === 'Done' || row.status === 'Completed' ? 'bg-green-100 text-green-800' :
                                                                                row.status === 'In Progress' ? 'bg-blue-100 text-blue-800' :
                                                                                'bg-gray-100 text-gray-800'
                                                                            }`}>
                                                                                {row.status}
                                                                            </span>
                                                                        </td>
                                                                        <td className="px-4 py-4 whitespace-nowrap text-xs align-top">
                                                                            <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                                                row.alignment_status === 'Aligned' ? 'bg-green-100 text-green-800' : 
                                                                                row.alignment_status === 'Misaligned' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                                                                            }`}>
                                                                                {row.alignment_status}
                                                                            </span>
                                                                        </td>
                                                                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-600 font-medium align-top">
                                                                            <div className="flex items-center gap-2">
                                                                                <div className="w-16 bg-gray-200 rounded-full h-1.5">
                                                                                    <div className="bg-blue-600 h-1.5 rounded-full" style={{ width: `${row.completion_percentage}%` }}></div>
                                                                                </div>
                                                                                {row.completion_percentage}%
                                                                            </div>
                                                                        </td>
                                                                        <td className="px-4 py-4 whitespace-nowrap text-xs align-top">
                                                                             <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                                                row.risk_level === 'Low' ? 'bg-green-100 text-green-800' : 
                                                                                row.risk_level === 'High' ? 'bg-red-100 text-red-800' : 'bg-orange-100 text-orange-800'
                                                                            }`}>
                                                                                {row.risk_level}
                                                                            </span>
                                                                        </td>
                                                                        <td className="px-4 py-4 text-xs text-gray-600 align-top leading-relaxed">
                                                                            {row.recommended_actions && row.recommended_actions.length > 0 ? (
                                                                                <ul className="list-disc list-inside space-y-1">
                                                                                    {row.recommended_actions.slice(0, 2).map((action, i) => (
                                                                                        <li key={i}>{action}</li>
                                                                                    ))}
                                                                                </ul>
                                                                            ) : '-'}
                                                                        </td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                                ) : agent.id === 'content-reviewer' && executionResult.report?.pages ? (
                                                    <div className="space-y-4">
                                                        <div className="bg-gray-50 border border-teal-100 rounded-xl p-6 relative overflow-hidden">
                                                            <div className="absolute top-0 right-0 p-4">
                                                                <div className="w-16 h-16 bg-teal-100 rounded-full flex items-center justify-center opacity-20">
                                                                    <FileText className="w-8 h-8 text-teal-800" />
                                                                </div>
                                                            </div>
                                                            <h3 className="text-xl font-bold text-gray-900 mb-1">Content Review Complete</h3>
                                                            <p className="text-gray-600 mb-4">
                                                                Analyzed {executionResult.report.summary.total_pages} page(s). Found {executionResult.report.summary.total_errors} issue(s).
                                                            </p>
                                                            <button
                                                                onClick={() => {
                                                                    localStorage.setItem('latest_content_review_report', JSON.stringify(executionResult.report));
                                                                    window.open('/content-review-dashboard', '_blank');
                                                                }}
                                                                className="px-5 py-2.5 bg-teal-600 text-white font-semibold rounded-lg hover:bg-teal-700 transition-colors shadow-md shadow-teal-200"
                                                            >
                                                                View Full Report ↗
                                                            </button>
                                                        </div>
                                                    </div>
                                                ) : agent.id === 'header-validator' && executionResult.report ? (
                                                    <div className="space-y-4">
                                                        <div className="bg-gray-50 border border-blue-100 rounded-xl p-6 relative overflow-hidden">
                                                            <div className="absolute top-0 right-0 p-4">
                                                                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center opacity-20">
                                                                    <Shield className="w-8 h-8 text-blue-800" />
                                                                </div>
                                                            </div>
                                                            <h3 className="text-xl font-bold text-gray-900 mb-1">Security Analysis Complete</h3>
                                                            <p className="text-gray-600 mb-4">
                                                                Score: {executionResult.report.security_score}. Found {executionResult.report.missing_headers.length} missing security headers.
                                                            </p>
                                                            <button
                                                                onClick={() => {
                                                                    localStorage.setItem('latest_header_report', JSON.stringify(executionResult.report));
                                                                    window.open('/header-validator-dashboard', '_blank');
                                                                }}
                                                                className="px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-md shadow-blue-200"
                                                            >
                                                                View Full Report ↗
                                                            </button>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="bg-gray-50 p-4 rounded-xl text-sm text-gray-700 whitespace-pre-wrap max-h-80 overflow-y-auto border border-gray-200 font-mono">
                                                        {executionResult.newsletter 
                                                            ? executionResult.newsletter 
                                                            : executionResult.analysis_result 
                                                                ? (
                                                                    <>
                                                                        {executionResult.analysis_result.status && (
                                                                            <div className={`mb-2 font-bold ${executionResult.analysis_result.status === 'Error' ? 'text-red-600' : 'text-green-600'}`}>
                                                                                Status: {executionResult.analysis_result.status}
                                                                            </div>
                                                                        )}
                                                                        <pre className="whitespace-pre-wrap font-mono text-xs">
                                                                            {JSON.stringify(executionResult.analysis_result, null, 2)}
                                                                        </pre>
                                                                    </>
                                                                )
                                                                : executionResult.report
                                                        }
                                                    </div>
                                                )}
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
