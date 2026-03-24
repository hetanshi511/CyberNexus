import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus, CheckCircle, Wallet, Laptop, ChevronDown, Mail, MessageSquare, BarChart, Ticket, Clipboard, ArrowRight } from 'lucide-react';

const accelerators = [
    { title: "AI for Healthcare", desc: "Create exceptional healthcare experiences and accelerate healthcare innovation", icon: Plus, color: "bg-green-50 text-green-600" },
    { title: "AI for Banking", desc: "Conversational AI assistant tailored for banking, enabling seamless customer interactions", icon: Wallet, color: "bg-orange-50 text-orange-600" },
    { title: "AI for HR", desc: "Drive employee productivity and experience through a unified interface for all HR tasks", icon: Laptop, color: "bg-purple-50 text-purple-600" }, /* Icon placeholder, assume general icon */
    { title: "AI for IT", desc: "Drive employee productivity and experience through a low touch ITSM automation experience", icon: Laptop, color: "bg-blue-50 text-blue-600" }
];

import { agents } from '../data/agents';

// ... (keep accelerators constant)

// Remove the local 'functions' constant as we will use 'agents' import

const IntegrationIcon = ({ type }) => {
    // ... (keep existing implementation)
    const colors = ["bg-orange-100 text-orange-600", "bg-green-100 text-green-600", "bg-blue-100 text-blue-600", "bg-purple-100 text-purple-600", "bg-gray-100 text-gray-600"];
    const colorClass = colors[type.length % colors.length];

    return (
        <div className={`w-6 h-6 rounded-md ${colorClass} flex items-center justify-center text-[10px] font-bold uppercase`}>
            {type.substring(0, 1)}
        </div>
    );
};

const AcceleratorsAndGrid = () => {
    const [activeFilter, setActiveFilter] = useState("All");
    const navigate = useNavigate();

    // Filter logic
    const filteredFunctions = activeFilter === "All"
        ? agents
        : agents.filter(agent => agent.function === activeFilter || agent.tags.includes(activeFilter));

    return (
        <section className="py-12 pb-32">
            <div className="container mx-auto px-6">

                {/* Accelerators Section */}
                <div className="mb-20">
                    <div className="mb-6">
                        <h2 className="text-xl font-semibold text-gray-800 mb-1">Browse by AI Accelerators</h2>
                        <p className="text-sm text-gray-500">View use cases filtered by industries and functions</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {accelerators.map((item, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 10 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: idx * 0.1 }}
                                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                                className="bg-white p-6 rounded-xl border border-transparent hover:border-blue-100 shadow-sm flex items-start gap-4 cursor-pointer"
                            >
                                <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${item.color}`}>
                                    <item.icon className="w-6 h-6" />
                                </div>
                                <div>
                                    <h3 className="text-base font-bold text-gray-900 mb-2">{item.title}</h3>
                                    <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    <div className="flex justify-center mt-8">
                        <button className="p-2 bg-white rounded-full shadow-sm border border-gray-100 hover:bg-gray-50 transition-colors">
                            <ChevronDown className="w-5 h-5 text-gray-400" />
                        </button>
                    </div>
                </div>

                {/* Functions Grid Section */}
                <div>
                    <div className="mb-8 flex items-end justify-between">
                        <div>
                            <h2 className="text-xl font-semibold text-gray-800 mb-1">Browse by Function</h2>
                            <p className="text-sm text-gray-500">AI agents for teams across your business</p>
                        </div>
                        <button
                            onClick={() => navigate('/search')}
                            className="text-blue-600 text-sm font-semibold hover:text-blue-700 flex items-center gap-1 transition-colors"
                        >
                            See all <ArrowRight className="w-4 h-4" />
                        </button>
                    </div>

                    <div className="flex flex-wrap gap-2 mb-10">
                        {["All", "Marketing", "HR", "IT", "Audit", "Compliance"].map(filter => (
                            <button
                                key={filter}
                                onClick={() => setActiveFilter(filter)}
                                className={`px-5 py-2 rounded-full text-xs font-medium transition-all ${activeFilter === filter
                                    ? 'bg-blue-600 text-white shadow-md shadow-blue-200'
                                    : 'bg-white text-gray-600 border border-transparent hover:border-gray-200 hover:bg-gray-50'
                                    }`}
                            >
                                {filter}
                            </button>
                        ))}
                    </div>


                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {filteredFunctions.map((func, idx) => (
                            <motion.div
                                key={idx}
                                layout
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                whileHover={{ y: -5, boxShadow: "0 10px 20px -5px rgba(0,0,0,0.05)" }}
                                onClick={() => navigate(`/agent/${func.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`)}
                                className="bg-white rounded-xl p-5 border border-blue-50/50 shadow-sm hover:shadow-md transition-all cursor-pointer relative overflow-hidden group"
                            >
                                <div className="h-24 bg-gradient-to-br from-blue-50 to-indigo-50/50 -m-5 mb-5 group-hover:from-blue-100/50 transition-colors"></div>

                                {/* Integration Icons - Floating over the header background */}
                                <div className="flex gap-2 -mt-8 mb-4 relative z-10 px-1">
                                    {func.integrations.map((int, i) => (
                                        <IntegrationIcon key={i} type={int} />
                                    ))}
                                    {func.integrations.length > 2 && (
                                        <div className="w-6 h-6 rounded-md bg-white border border-gray-100 flex items-center justify-center text-[10px] text-gray-500 font-bold shadow-sm">
                                            +1
                                        </div>
                                    )}
                                </div>

                                {/* Custom Badge if present */}
                                {func.badge && (
                                    <div className="absolute top-3 right-3 bg-blue-100 text-blue-700 text-[10px] font-bold px-2 py-1 rounded shadow-sm">
                                        {func.badge}
                                    </div>
                                )}

                                <h3 className="text-sm font-bold text-gray-900 mb-2 line-clamp-1" title={func.title}>{func.title}</h3>
                                <p className="text-xs text-gray-500 mb-4 line-clamp-2 leading-relaxed h-8">
                                    {func.description || func.desc}
                                </p>

                                <div className="flex flex-wrap gap-2 mt-auto">
                                    {func.tags.map((tag, tIdx) => (
                                        <span key={tIdx} className="px-2 py-1 bg-gray-50 rounded text-[10px] font-medium text-gray-500 border border-gray-100">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>

            </div>
        </section>
    );
};

export default AcceleratorsAndGrid;
