import React from 'react';
import { Facebook, Twitter, Linkedin, Youtube, Instagram } from 'lucide-react';

const Footer = () => {
    return (
        <footer className="bg-gray-900 text-white py-16">
            <div className="container mx-auto px-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 mb-12">

                    {/* Brand Column */}
                    <div className="lg:col-span-2">
                        <div className="flex items-center gap-2 mb-6">
                            <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
                                <span className="text-gray-900 font-bold text-lg">I</span>
                            </div>
                            <span className="text-xl font-bold tracking-tight">Infopercept</span>
                        </div>
                        <p className="text-gray-400 leading-relaxed mb-6 pr-8">
                            The world's leading enterprise AI platform. Optimize customer and employee experiences with Conversational AI and Generative AI.
                        </p>
                        <div className="flex gap-4">
                            {[Twitter, Linkedin, Facebook, Youtube, Instagram].map((Icon, idx) => (
                                <a key={idx} href="#" className="p-2 bg-gray-800 rounded-full hover:bg-blue-600 transition-colors">
                                    <Icon className="w-4 h-4" />
                                </a>
                            ))}
                        </div>
                    </div>

                    {/* Links Columns */}
                    <div>
                        <h4 className="font-bold text-lg mb-6">Platform</h4>
                        <ul className="space-y-4 text-gray-400">
                            {['Overview', 'XO Platform', 'SearchAssist', 'SmartAssist', 'AgentAssist'].map(link => (
                                <li key={link}><a href="#" className="hover:text-white transition-colors">{link}</a></li>
                            ))}
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-bold text-lg mb-6">Company</h4>
                        <ul className="space-y-4 text-gray-400">
                            {['About Us', 'Careers', 'Partners', 'Newsroom', 'Contact'].map(link => (
                                <li key={link}><a href="#" className="hover:text-white transition-colors">{link}</a></li>
                            ))}
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-bold text-lg mb-6">Resources</h4>
                        <ul className="space-y-4 text-gray-400">
                            {['Documentation', 'Developers', 'Community', 'Blog', 'Case Studies'].map(link => (
                                <li key={link}><a href="#" className="hover:text-white transition-colors">{link}</a></li>
                            ))}
                        </ul>
                    </div>
                </div>

                <div className="pt-8 border-t border-gray-800 text-center md:text-left flex flex-col md:flex-row justify-between items-center text-sm text-gray-500">
                    <p>&copy; 2024 Infopercept. All Rights Reserved.</p>
                    <div className="flex gap-6 mt-4 md:mt-0">
                        <a href="#" className="hover:text-white">Privacy Policy</a>
                        <a href="#" className="hover:text-white">Terms of Use</a>
                        <a href="#" className="hover:text-white">Cookie Policy</a>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
