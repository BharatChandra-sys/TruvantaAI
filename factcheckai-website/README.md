# TruvantaAI Website

Public-facing website for the TruvantaAI browser extension, including privacy policy, terms of service, and feature documentation.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

Open [http://localhost:3000](http://localhost:3000) to view the website.

## 📁 Project Structure

```
TruvantaAI-website/
├── app/
│   ├── layout.tsx           # Root layout with metadata
│   ├── page.tsx              # Homepage
│   ├── globals.css           # Tailwind CSS + theme config
│   ├── privacy/page.tsx      # Privacy Policy (GDPR/CCPA compliant)
│   ├── terms/page.tsx        # Terms of Service
│   └── support/page.tsx      # Support & Contact page
├── components/
│   ├── Header.tsx            # Navigation header
│   ├── Footer.tsx            # Site footer with links
│   ├── HeroSection.tsx       # Main hero with extension preview
│   ├── TrustStrip.tsx        # Capability badges
│   ├── ClaimChecker.tsx      # Interactive demo
│   ├── HowItWorks.tsx        # 4-step pipeline explanation
│   ├── EvidenceSection.tsx   # Source database info
│   ├── TechnologySection.tsx # Technical stack overview
│   ├── BrowserExtension.tsx  # Browser integration demo
│   ├── UncertaintySection.tsx# Verdict system explanation
│   ├── TransparencySection.tsx# Audit trail example
│   ├── OpenSourceSection.tsx # GitHub stats & community
│   ├── FAQSection.tsx        # Accordion FAQ
│   └── CTASection.tsx        # Final call-to-action
├── public/                   # Static assets (logo, etc.)
├── postcss.config.mjs        # PostCSS + Tailwind config
├── next.config.ts            # Next.js configuration
├── package.json              # Dependencies
└── tsconfig.json             # TypeScript config
```

## 🎨 Design System

Built with **Tailwind CSS v4** using TruvantaAI brand colors:

### Brand Colors
- **Primary Accent**: `#c0c1ff` (lavender) - `surface-tint`
- **AI Orange**: `#f59e0b` - `ai-orange`
- **Secondary**: `#62dcad` (green) - `secondary`
- **Tertiary**: `#ffe083` (yellow) - `tertiary`
- **Error**: `#ffb4ab` (red) - `error`

### Surface Colors (Dark Theme)
- **Background**: `#101419` - `surface`
- **Container Low**: `#181c21` - `surface-container-low`
- **Container**: `#1c2025` - `surface-container`
- **Container High**: `#262a30` - `surface-container-high`
- **Container Highest**: `#31353a` - `surface-container-highest`

### Typography
- **Body**: Inter (400, 500, 600, 700)
- **Mono**: JetBrains Mono (400, 500, 600)
- **Icons**: Material Symbols Outlined

## 📄 Legal Pages

### Privacy Policy (`/privacy`)
- GDPR compliant (EU users)
- CCPA compliant (California users)
- Microsoft Edge Add-ons policy compliant
- Zero data collection guarantee
- Third-party service disclosure
- User rights explanation

### Terms of Service (`/terms`)
- Acceptable use policy
- Intellectual property (MIT License)
- Disclaimers & limitations
- User responsibilities
- Service modification rights

### Support (`/support`)
- Bug reporting (GitHub Issues)
- Community forum (Discussions)
- Email contacts
- Security vulnerability disclosure
- FAQ section

## 🔧 Technology Stack

- **Framework**: Next.js 16.3.5 (App Router)
- **Styling**: Tailwind CSS v4
- **Language**: TypeScript
- **Icons**: Material Symbols Outlined
- **Fonts**: Inter, JetBrains Mono (Google Fonts)

## 🚀 Deployment to Vercel

### Option 1: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

### Option 2: GitHub Integration

1. Push code to GitHub repository
2. Visit [vercel.com](https://vercel.com)
3. Click "Import Project"
4. Select your GitHub repository
5. Configure build settings (auto-detected)
6. Click "Deploy"

### Build Configuration

Vercel auto-detects Next.js projects. No configuration needed.

**Build Command**: `npm run build`  
**Output Directory**: `.next`  
**Install Command**: `npm install`

## 🔗 Privacy Policy URL

After deploying to Vercel, update the extension's `manifest.json`:

```json
{
  "privacy_policy": "https://your-domain.vercel.app/privacy"
}
```

## 📝 Post-Deployment Checklist

- [ ] Verify all pages load correctly
- [ ] Test responsive design (mobile, tablet, desktop)
- [ ] Validate privacy policy URL works
- [ ] Update extension manifest with privacy policy URL
- [ ] Submit extension to Chrome/Edge stores
- [ ] Test all navigation links
- [ ] Verify GitHub links point to correct repo
- [ ] Update README with live URL

## 🛠️ Development

```bash
# Run dev server with Turbopack
npm run dev

# Type checking
npm run type-check

# Lint code
npm run lint

# Build for production
npm run build

# Preview production build
npm start
```

## 📦 Environment Variables

No environment variables required. All configuration is in `next.config.ts` and `globals.css`.

## 🎯 SEO & Metadata

Configured in `app/layout.tsx`:

- **Title**: "TruvantaAI - AI-Powered Fact Verification"
- **Description**: "Open-source browser extension for instant fact-checking with ML models and evidence retrieval"
- **Keywords**: fact-checking, AI, machine learning, browser extension, misinformation
- **Viewport**: Responsive, mobile-optimized
- **Icons**: Favicon configured

## 📱 Browser Support

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support (iOS 15+)
- Opera: ✅ Full support

## 🤝 Contributing

This website is part of the TruvantaAI open-source project. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](../LICENSE) file

## 🔗 Related Links

- **Extension Repository**: [GitHub](https://github.com/yourusername/TruvantaAI)
- **Backend API**: [Render.com](https://factcheckai-gjrk.onrender.com)
- **Documentation**: [Wiki](https://github.com/yourusername/TruvantaAI/wiki)
- **Discord**: [Community Server](https://discord.gg/TruvantaAI)

---

Built with ❤️ by the TruvantaAI community
