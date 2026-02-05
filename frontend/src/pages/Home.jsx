import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import Solutions from '../components/Solutions';
import AcceleratorsAndGrid from '../components/AcceleratorsAndGrid';
import Footer from '../components/Footer';

function Home() {
    return (
        <>
            <main>
                <Hero />
                <Solutions />
                <AcceleratorsAndGrid />
            </main>
        </>
    );
}

export default Home;
