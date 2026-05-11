import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import "./App.css";

import { AuthProvider } from "./lib/auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import PropertyDetail from "./pages/PropertyDetail";
import ScrapeCounty from "./pages/ScrapeCounty";
import SavedSearches from "./pages/SavedSearches";
import Leaderboard from "./pages/Leaderboard";

function App() {
  return (
    <div className="App swiss-shadcn">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/leaderboard" element={<Leaderboard />} />
            <Route path="/property/:id" element={<PropertyDetail />} />
            <Route path="/scrape" element={<ScrapeCounty />} />
            <Route path="/saved" element={<SavedSearches />} />
          </Routes>
        </BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              borderRadius: 0,
              border: "1px solid #18181B",
              fontFamily: "'IBM Plex Sans', sans-serif",
            },
          }}
        />
      </AuthProvider>
    </div>
  );
}

export default App;
