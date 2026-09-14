import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import LiveCamera from "./pages/LiveCamera.jsx";
import Detections from "./pages/Detections.jsx";
import Search from "./pages/Search.jsx";
import DetectionDetails from "./pages/DetectionDetails.jsx";
import Statistics from "./pages/Statistics.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/live" element={<LiveCamera />} />
        <Route path="/detections" element={<Detections />} />
        <Route path="/detections/:id" element={<DetectionDetails />} />
        <Route path="/search" element={<Search />} />
        <Route path="/statistics" element={<Statistics />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
