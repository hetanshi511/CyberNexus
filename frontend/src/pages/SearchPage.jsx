import React, { useState, useEffect } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ChevronDown, ChevronRight, X, ArrowLeft } from 'lucide-react';
import { agents, filters } from '../data/agents';

// Reusing the IntegrationIcon logic (simplified)
const IntegrationIcon = ({ type }) => {
    const colors = ["bg-orange-100 text-orange-600", "bg-green-100 text-green-600", "bg-blue-100 text-blue-600", "bg-purple-100 text-purple-600", "bg-gray-100 text-gray-600"];
    const colorClass = colors[type.length % colors.length];
    return (
        <div className={`w-6 h-6 rounded-md ${colorClass} flex items-center justify-center text-[10px] font-bold uppercase`}>
            {type.substring(0, 1)}
        </div>
    );
};

const FilterSection = ({ title, options, selected, onChange, isOpen, toggleOpen }) => {
    return (
        <div className="border-b border-gray-100 py-4">
            <button
                className="flex items-center justify-between w-full text-left font-medium text-gray-700 hover:text-blue-600 transition-colors"
                onClick={toggleOpen}
            >
                {title}
                {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="pt-3 space-y-2">
                            {options.map(option => (
                                <label key={option} className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={selected.includes(option)}
                                        onChange={() => onChange(option)}
                                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-100"
                                    />
                                    {option}
                                </label>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const SearchPage = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const navigate = useNavigate();
    const query = searchParams.get('q') || '';

    // State for filters
    const [selectedFilters, setSelectedFilters] = useState({
        industries: [],
        functions: [],
        useCases: [],
        agentTypes: [],
        integrations: []
    });

    const [openSections, setOpenSections] = useState({
        industries: true,
        functions: false,
        useCases: false,
        agentTypes: false,
        integrations: false
    });

    // Handle Search Input
    const handleSearchChange = (e) => {
        setSearchParams({ q: e.target.value });
    };

    const toggleFilter = (category, value) => {
        setSelectedFilters(prev => {
            const current = prev[category];
            const updated = current.includes(value)
                ? current.filter(item => item !== value)
                : [...current, value];
            return { ...prev, [category]: updated };
        });
    };

    // Filter Logic
    const filteredAgents = agents.filter(agent => {
        const matchesQuery = agent.title.toLowerCase().includes(query.toLowerCase()) ||
            agent.description.toLowerCase().includes(query.toLowerCase());

        const matchesIndustry = selectedFilters.industries.length === 0 || selectedFilters.industries.includes(agent.industry);
        const matchesFunction = selectedFilters.functions.length === 0 || selectedFilters.functions.includes(agent.function);
        // Simplified matching for other categories just for demo

        return matchesQuery && matchesIndustry && matchesFunction;
    });

    return (
        <div className="min-h-screen bg-[#f8fbff] pt-20 pb-12">
            <div className="container mx-auto px-6 max-w-7xl">

                {/* Header & Breadcrumbs */}
                <div className="mb-8">
                    <Link to="/" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-blue-600 mb-4 transition-colors">
                        <ArrowLeft className="w-4 h-4" /> Back
                    </Link>
                    <div className="flex items-center gap-2 text-sm text-gray-400 mb-4">
                        <span>Marketplace</span>
                        <ChevronRight className="w-3 h-3" />
                        <span className="text-gray-900 font-medium">Search</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold text-gray-900">Search Results</h1>
                        {filteredAgents.length > 0 && (
                            <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
                                {filteredAgents.length}
                            </span>
                        )}
                    </div>
                </div>

                <div className="flex flex-col lg:flex-row gap-8">

                    {/* Sidebar Filters */}
                    <aside className="w-full lg:w-64 flex-shrink-0">
                        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm sticky top-24">
                            <h3 className="font-semibold text-gray-900 mb-4">Filters</h3>

                            <FilterSection
                                title="Industry"
                                options={filters.industries}
                                selected={selectedFilters.industries}
                                onChange={(val) => toggleFilter('industries', val)}
                                isOpen={openSections.industries}
                                toggleOpen={() => setOpenSections(prev => ({ ...prev, industries: !prev.industries }))}
                            />
                            <FilterSection
                                title="Function"
                                options={filters.functions}
                                selected={selectedFilters.functions}
                                onChange={(val) => toggleFilter('functions', val)}
                                isOpen={openSections.functions}
                                toggleOpen={() => setOpenSections(prev => ({ ...prev, functions: !prev.functions }))}
                            />
                            <FilterSection
                                title="Use Case"
                                options={filters.useCases}
                                selected={selectedFilters.useCases}
                                onChange={(val) => toggleFilter('useCases', val)}
                                isOpen={openSections.useCases}
                                toggleOpen={() => setOpenSections(prev => ({ ...prev, useCases: !prev.useCases }))}
                            />
                            <FilterSection
                                title="Agent Type"
                                options={filters.agentTypes}
                                selected={selectedFilters.agentTypes}
                                onChange={(val) => toggleFilter('agentTypes', val)}
                                isOpen={openSections.agentTypes}
                                toggleOpen={() => setOpenSections(prev => ({ ...prev, agentTypes: !prev.agentTypes }))}
                            />
                            <FilterSection
                                title="Integration"
                                options={filters.integrations}
                                selected={selectedFilters.integrations}
                                onChange={(val) => toggleFilter('integrations', val)}
                                isOpen={openSections.integrations}
                                toggleOpen={() => setOpenSections(prev => ({ ...prev, integrations: !prev.integrations }))}
                            />
                        </div>
                    </aside>

                    {/* Main Content */}
                    <div className="flex-1">

                        {/* Quick Filters */}
                        <div className="flex flex-wrap gap-3 mb-6">
                            {['AI for Process', 'AI for Work', 'AI for Service'].map(tag => (
                                <button key={tag} className="px-5 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-600 hover:border-blue-300 hover:text-blue-600 hover:shadow-sm transition-all">
                                    {tag}
                                </button>
                            ))}
                        </div>

                        {/* Search Input */}
                        <div className="relative mb-8">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
                            <input
                                type="text"
                                value={query}
                                onChange={handleSearchChange}
                                placeholder="Type and press Enter to search"
                                className="w-full pl-12 pr-4 py-4 bg-white border border-gray-200 rounded-xl text-gray-700 focus:ring-2 focus:ring-blue-100 focus:border-blue-400 outline-none shadow-sm transition-all"
                            />
                        </div>

                        {/* Results Grid */}
                        {filteredAgents.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {filteredAgents.map(agent => (
                                    <motion.div
                                        key={agent.id}
                                        layout
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        whileHover={{ y: -5, boxShadow: "0 10px 20px -5px rgba(0,0,0,0.05)" }}
                                        onClick={() => navigate(`/agent/${agent.id}`)}
                                        className="bg-white rounded-xl p-5 border border-blue-50/50 shadow-sm hover:shadow-md transition-all cursor-pointer relative overflow-hidden group flex flex-col h-[280px]"
                                    >
                                        <div className="h-24 bg-gradient-to-br from-blue-50 to-indigo-50/50 -m-5 mb-5 group-hover:from-blue-100/50 transition-colors"></div>

                                        <div className="flex gap-2 -mt-8 mb-4 relative z-10 px-1">
                                            {agent.integrations.map((int, i) => (
                                                <IntegrationIcon key={i} type={int} />
                                            ))}
                                        </div>

                                        {agent.badge && (
                                            <div className="absolute top-3 right-3 bg-blue-100 text-blue-700 text-[10px] font-bold px-2 py-1 rounded shadow-sm">
                                                {agent.badge}
                                            </div>
                                        )}

                                        <h3 className="text-sm font-bold text-gray-900 mb-2 line-clamp-1">{agent.title}</h3>
                                        <p className="text-xs text-gray-500 mb-4 line-clamp-2 leading-relaxed">
                                            {agent.description}
                                        </p>

                                        <div className="flex flex-wrap gap-2 mt-auto">
                                            {agent.tags.map((tag, tIdx) => (
                                                <span key={tIdx} className="px-2 py-1 bg-gray-50 rounded text-[10px] font-medium text-gray-500 border border-gray-100">
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-gray-200">
                                <div className="mx-auto w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
                                    <Search className="w-8 h-8 text-gray-300" />
                                </div>
                                <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
                                <p className="text-gray-500 max-w-sm mx-auto">
                                    We couldn't find any agents matching "{query}". Try adjusting your filters or search terms.
                                </p>
                                <button
                                    onClick={() => { setSearchParams({ q: '' }); setSelectedFilters({ industries: [], functions: [], useCases: [], agentTypes: [], integrations: [] }) }}
                                    className="mt-6 px-4 py-2 text-blue-600 font-medium hover:bg-blue-50 rounded-lg transition-colors"
                                >
                                    Clear all filters
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SearchPage;
