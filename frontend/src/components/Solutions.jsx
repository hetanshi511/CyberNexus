import React from 'react';
import { motion } from 'framer-motion';

const solutions = [
    {
        title: "AI for Work",
        description: "Enhance employee productivity through information discovery, task automation, and cross-organizational collaboration",
        delay: 0
    },
    {
        title: "AI for Service",
        description: "Automate customer interactions across channels with agentic solutions for contact centers and self-service",
        delay: 0.1
    },
    {
        title: "AI for Process",
        description: "Automate knowledge-intensive tasks and transform complex workflows into agent-driven processes",
        delay: 0.2
    }
];

const Solutions = () => {
    return (
        <section className="py-8">
            <div className="container mx-auto px-6">
                <div className="mb-6">
                    <h2 className="text-xl font-semibold text-gray-800 mb-1">Browse by AI Solutions</h2>
                    <p className="text-sm text-gray-500">View use cases filtered by each of our solutions</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {solutions.map((item, idx) => (
                        <motion.div
                            key={idx}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: item.delay, duration: 0.5 }}
                            whileHover={{ y: -5, boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.05)" }}
                            className="bg-white p-8 rounded-2xl border border-transparent hover:border-blue-100 shadow-sm transition-all cursor-pointer h-full flex flex-col items-start"
                        >
                            {/* Blue Circle Loader Icon Replica */}
                            <div className="mb-6 relative w-10 h-10">
                                <div className="absolute inset-0 rounded-full border-4 border-blue-100"></div>
                                <div className="absolute inset-0 rounded-full border-4 border-blue-600 border-t-transparent border-l-transparent -rotate-45"></div>
                            </div>

                            <h3 className="text-lg font-bold text-gray-900 mb-3">{item.title}</h3>
                            <p className="text-sm text-gray-500 leading-relaxed">
                                {item.description}
                            </p>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default Solutions;
