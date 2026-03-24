import React from 'react';

const Footer = () => {
    return (
        <footer className="bg-gray-900 text-white py-16">
            <div className="container mx-auto px-6">
                <div className="mb-12">
                    {/* Brand Column */}
                    <div className="max-w-sm">
                        <div className="flex items-center gap-2 mb-6">
                            <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
                                <span className="text-gray-900 font-bold text-lg">I</span>
                            </div>
                            <span className="text-xl font-bold tracking-tight">Infopercept</span>
                        </div>
                        <p className="text-gray-400 leading-relaxed pr-8">
                            The world's leading enterprise AI platform. Optimize customer and employee experiences with Conversational AI and Generative AI.
                        </p>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
