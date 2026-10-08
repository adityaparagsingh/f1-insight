import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Seasons from './pages/Seasons'
import Drivers from './pages/Drivers'
import DriverDetail from './pages/DriverDetail'
import Constructors from './pages/Constructors'
import ConstructorDetail from './pages/ConstructorDetail'
import Circuits from './pages/Circuits'
import CircuitDetail from './pages/CircuitDetail'
import Races from './pages/Races'
import RaceDetail from './pages/RaceDetail'
import Olap from './pages/Olap'
import Mining from './pages/Mining'
import Insights from './pages/Insights'
import About from './pages/About'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="seasons" element={<Seasons />} />
        <Route path="drivers" element={<Drivers />} />
        <Route path="drivers/:id" element={<DriverDetail />} />
        <Route path="constructors" element={<Constructors />} />
        <Route path="constructors/:id" element={<ConstructorDetail />} />
        <Route path="circuits" element={<Circuits />} />
        <Route path="circuits/:id" element={<CircuitDetail />} />
        <Route path="races" element={<Races />} />
        <Route path="races/:id" element={<RaceDetail />} />
        <Route path="olap" element={<Olap />} />
        <Route path="mining" element={<Mining />} />
        <Route path="insights" element={<Insights />} />
        <Route path="about" element={<About />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
