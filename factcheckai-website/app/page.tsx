import Header from '@/components/Header';
import Footer from '@/components/Footer';
import MotionProvider from '@/components/landing/MotionProvider';
import Hero from '@/components/landing/Hero';
import Walkthrough from '@/components/landing/Walkthrough';
import LiveCheck from '@/components/landing/LiveCheck';
import Evidence from '@/components/landing/Evidence';
import Sources from '@/components/landing/Sources';
import Verdicts from '@/components/landing/Verdicts';
import Measured from '@/components/landing/Measured';
import Privacy from '@/components/landing/Privacy';
import FAQ, { Closing } from '@/components/landing/FAQ';

export default function Home() {
  return (
    <MotionProvider>
      <Header />
      <main>
        <Hero />
        <Walkthrough />
        <LiveCheck />
        <Evidence />
        <Sources />
        <Verdicts />
        <Measured />
        <Privacy />
        <FAQ />
        <Closing />
      </main>
      <Footer />
    </MotionProvider>
  );
}
