import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const FloatingIcon = ({ icon: Icon, className, delay }) => (
    <motion.div
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1, y: [0, -10, 0] }}
        transition={{
            opacity: { duration: 0.5, delay },
            scale: { duration: 0.5, delay },
            y: { duration: 4, repeat: Infinity, ease: "easeInOut" }
        }}
        className={`absolute hidden lg:flex items-center justify-center bg-white rounded-xl shadow-lg border border-gray-100 p-3 ${className}`}
    >
        <Icon className="w-6 h-6 text-gray-400 opacity-80" />
    </motion.div>
);

const Hero = () => {
    const [query, setQuery] = useState('');
    const navigate = useNavigate();

    const handleSearch = (e) => {
        e.preventDefault();
        if (query.trim()) {
            navigate(`/search?q=${encodeURIComponent(query)}`);
        }
    };

    return (
        <section className="relative pt-16 pb-24 overflow-hidden">
            {/* Floating Background Elements */}
            {/* ... existing floating elements */}

            <div className="container mx-auto px-6 relative z-10">
                <div className="max-w-4xl mx-auto text-center">
                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                        className="text-4xl md:text-5xl font-semibold text-gray-900 mb-10 leading-tight tracking-tight"
                    >
                        Explore <span className="text-blue-600">agent templates</span> and <span className="text-blue-600">integrations</span> <br />
                        for your business.
                    </motion.h1>

                    {/* Search Bar */}
                    <motion.form
                        onSubmit={handleSearch}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.5, delay: 0.2 }}
                        className="relative max-w-2xl mx-auto mb-10 group"
                    >
                        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                            <Search className="h-5 w-5 text-blue-500" />
                        </div>
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            className="block w-full pl-11 pr-12 py-4 bg-white border border-blue-100 rounded-full text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xl shadow-blue-50/50 transition-all text-base"
                            placeholder="Search agent templates..."
                        />
                        <button type="submit" className="absolute inset-y-0 right-2 flex items-center pr-2">
                            <div className="p-2 bg-gray-100 rounded-full text-gray-400 group-focus-within:bg-blue-600 group-focus-within:text-white transition-colors cursor-pointer">
                                <ArrowRight className="w-4 h-4" />
                            </div>
                        </button>
                    </motion.form>


                </div>
            </div>
        </section>
    );
};

export default Hero;
