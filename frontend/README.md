# Infopercept Marketplace

A modern AI Agent Marketplace built with React, Vite, and Tailwind CSS.

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or higher)
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (Optional, for containerized run)

### Option 1: Run with Docker (Recommended)

The easiest way to run the application is using Docker. This ensures you have the exact same environment as production.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/meet306/invinsense-marketplace.git
    cd invinsense-marketplace/frontend
    ```

2.  **Start the app:**
    ```bash
    docker-compose up --build
    ```

3.  **Access the app:**
    Open [http://localhost:3000](http://localhost:3000) in your browser.

### Option 2: Run Manually (Local Development)

1.  **Install dependencies:**
    ```bash
    npm install
    ```

2.  **Set up Environment Variables:**
    Create a `.env` file in the `frontend` directory using the provided `.env.example` as a template.
    *(Note: If you have just cloned the repo, check if the `.env` file is already present).*

3.  **Start the development server:**
    ```bash
    npm run dev
    ```

4.  **Access the app:**
    Open [http://localhost:5173](http://localhost:5173) in your browser.

## 🛠️ Tech Stack

- **Frontend:** React, Vite
- **Styling:** Tailwind CSS, Framer Motion
- **Icons:** Lucide React
- **Auth:** Firebase Authentication
