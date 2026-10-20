import Header from '@/components/Header';
import Footer from '@/components/Footer';
import MotionProvider from '@/components/landing/MotionProvider';
import Hero from '@/components/landing/Hero';
import Walkthrough from '@/components/landing/Walkthrough';
import Evidence from '@/components/landing/Evidence';
import Verdicts from '@/components/landing/Verdicts';
import Privacy from '@/components/landing/Privacy';
import FAQ, { Closing } from '@/components/landing/FAQ';

export default function Home() {
  return (
    <MotionProvider>
      <Header />
      <main>
        <Hero />
        <Walkthrough />
        <Evidence />
        <Verdicts />
        <Privacy />
        <FAQ />
        <Closing />
      </main>
      <Footer />
    </MotionProvider>
  );
}
