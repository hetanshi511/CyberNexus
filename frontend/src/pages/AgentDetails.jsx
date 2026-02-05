import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ChevronRight, Copy, Check, Download, MessageSquare, Shield, Zap } from 'lucide-react';
import { agents } from '../data/agents';

const AgentDetails = () => {
    const { id } = useParams();
    const [agent, setAgent] = useState(null);
    const [pageTitle, setPageTitle] = useState('');
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        // Find agent by ID
        let foundAgent = agents.find(a => a.id === id);

        // Fallback for demo if id not found (or coming from Accelerators grid with title match)
        if (!foundAgent && id) {
            // Try finding by title slug if id lookup fails
            foundAgent = agents.find(a =>
                a.title.toLowerCase().replace(/[^a-z0-9]+/g, '-') === id ||
                a.title === id
            );
        }

        // If still not found, just use the first one or a mock for demo purposes if strictly needed, 
        // but better to show not found or handle gracefully. 
        // For this task, we assume valid IDs are passed.

        if (foundAgent) {
            setAgent(foundAgent);
            setPageTitle(foundAgent.title);
        }
    }, [id]);

    if (!agent) {
        return (
            <div className="min-h-screen pt-24 text-center">
                <p>Loading agent details...</p>
                <Link to="/search" className="text-blue-600 hover:underline">Return to Search</Link>
            </div>
        );
    }

    const handleCopy = () => {
        navigator.clipboard.writeText(agent.prompt || "Default prompt text...");
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

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
                                                    <div className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold uppercase ${integration === 'slack' ? 'bg-purple-100 text-purple-700' :
                                                        integration === 'gmail' ? 'bg-red-100 text-red-700' :
                                                            integration === 'zendesk' ? 'bg-green-100 text-green-700' :
                                                                'bg-gray-100 text-gray-700'
                                                        }`}>
                                                        {integration.charAt(0)}
                                                    </div>
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
                                <button className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700 hover:shadow-xl transition-all active:scale-95">
                                    Install
                                </button>
                                <button className="px-8 py-3 bg-white text-gray-700 font-semibold rounded-xl border border-gray-200 hover:bg-gray-50 hover:border-gray-300 transition-all active:scale-95">
                                    Contact Sales
                                </button>
                            </div>
                        </div>

                        {/* Right Column: Visual */}
                        <div className="relative">
                            <div className="aspect-[4/3] bg-gradient-to-br from-blue-50 to-indigo-50 rounded-3xl border border-blue-100 flex items-center justify-center relative overflow-hidden group">
                                {/* Decor circles */}
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
                                {agent.prompt || `Given the document at <Document>, identify its main topics, sections, and key points. Then, draft a list of frequently asked questions (FAQs) based on this information. Start the response by empathizing with the user's emotions, and provide reassurance. The response should be clear and structured, using bullet points for each FAQ. The welcome should be similar to 'Sure! Let's draft an FAQ document based on the provided document.' but not identical.`}
                            </p>
                        </div>
                    </div>

                </div>

                {/* Bottom Section - Installation / Screenshots */}
                <div className="mt-8 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                    <button className="w-full flex items-center justify-between p-6 text-left hover:bg-gray-50 transition-colors">
                        <div className="flex items-center gap-2">
                            <span className="font-semibold text-gray-900">Installation Instructions</span>
                        </div>
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                    </button>
                    <div className="px-6 pb-6 text-gray-600 text-sm">
                        Instructions to follow while configuring the agent.
                    </div>
                </div>

                <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div className="p-6 bg-white rounded-xl border border-gray-100 shadow-sm text-center">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Developer</p>
                        <p className="font-medium text-gray-900">Infopercept</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl border border-gray-100 shadow-sm text-center">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Last Updated</p>
                        <p className="font-medium text-gray-900">15-12-2025</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl border border-gray-100 shadow-sm text-center">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Language</p>
                        <p className="font-medium text-gray-900">English</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl border border-gray-100 shadow-sm text-center">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Installs</p>
                        <p className="font-medium text-gray-900">-</p>
                    </div>
                </div>

            </div>
        </div>
    );
};

const ChevronDown = ({ className }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="m6 9 6 6 6-6" /></svg>
);

export default AgentDetails;
