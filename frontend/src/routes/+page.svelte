<script lang="ts">
    import PublicNav from '$lib/components/site/PublicNav.svelte';
    import AuthCard from '$lib/components/site/AuthCard.svelte';
    import ShapeWaves from '$lib/components/site/ShapeWaves.svelte';
    import { t } from '$lib/i18n';
    import { tick, onMount } from 'svelte';
    import { slide } from 'svelte/transition';
    import { cubicOut } from 'svelte/easing';
    import { page } from '$app/stores';
    import type { PageData, ActionData } from './$types';
    import { Renderer, Triangle, Program, Mesh, Texture } from 'ogl';
    import { gsap } from 'gsap';

    export let data: PageData;
    export let form: ActionData;

    type ViewSection = 'jak-to-dziala' | 'o-wa-gone' | 'kontakt';
    let currentView: ViewSection = 'jak-to-dziala'; 

    let isLightMode = false;

    let cursorX = 0;
    let cursorY = 0;
    let cursorVisible = false;
    let cursorHover = false;

    $: features = [
        {
            id: 'network',
            tag: $t('landing.features.network.title'),
            copy: $t('landing.features.network.copy'),
            imgDark: '/features/dot_white_1.png',
            imgLight: '/features/dot_black_1.png'
        },
        {
            id: 'incidents',
            tag: $t('landing.features.incidents.title'),
            copy: $t('landing.features.incidents.copy'),
            imgDark: '/features/dot_white_2.png',
            imgLight: '/features/dot_black_2.png'
        },
        {
            id: 'timetable',
            tag: $t('landing.features.timetable.title'),
            copy: $t('landing.features.timetable.copy'),
            imgDark: '/features/dot_white_3.png',
            imgLight: '/features/dot_black_3.png'
        },
        {
            id: 'scenarios',
            tag: $t('landing.features.scenarios.title'),
            copy: $t('landing.features.scenarios.copy'),
            imgDark: '/features/dot_white_4.png',
            imgLight: '/features/dot_black_4.png'
        }
    ];

    $: faqItems = [
        {
            question: $t('landing.faq.q1.question'),
            answer: $t('landing.faq.q1.answer')
        },
        {
            question: $t('landing.faq.q2.question'),
            answer: $t('landing.faq.q2.answer')
        },
        {
            question: $t('landing.faq.q3.question'),
            answer: $t('landing.faq.q3.answer')
        },
        {
            question: $t('landing.faq.q4.question'),
            answer: $t('landing.faq.q4.answer')
        },
        {
            question: 'Jak zintegrować API z zewnętrznym systemem?',
            answer: 'Oferujemy standardowe endpointy REST oraz WebSocket ze strumieniem zdarzeń w czasie rzeczywistym.'
        }
    ];

    let activeFeature = 0;
    let openFaqIndex: number | null = 0;

    let displayedTag = '';
    let displayedCopy = '';
    let typewriterTimer: ReturnType<typeof setTimeout>;

    function runTypewriter(index: number) {
        if (!features[index]) return;
        
        const targetTag = features[index].tag;
        const targetCopy = ' ' + features[index].copy;
        
        displayedTag = '';
        displayedCopy = '';
        clearTimeout(typewriterTimer);

        let tagIndex = 0;
        let copyIndex = 0;

        const type = () => {
            if (tagIndex < targetTag.length) {
                displayedTag += targetTag[tagIndex];
                tagIndex++;
                typewriterTimer = setTimeout(type, 30);
            } else if (copyIndex < targetCopy.length) {
                displayedCopy += targetCopy[copyIndex];
                copyIndex++;
                typewriterTimer = setTimeout(type, 15);
            }
        };
        type();
    }

    $: runTypewriter(activeFeature);

    let engine: any = null;
    let morphContainer: HTMLElement;
    let startX = 0;
    let dragWidth = 1;
    let activeDrag = false;

    const TRANSITIONS: Record<string, number> = { melt: 0, ripple: 1, shear: 2, swirl: 3 };

    const vertexShader = `
    attribute vec2 position;
    attribute vec2 uv;
    varying vec2 vUv;
    void main() {
        vUv = uv;
        gl_Position = vec4(position, 0.0, 1.0);
    }`;

    // Zmodyfikowany fragmentShader na "object-fit: contain"
    const fragmentShader = `
    precision highp float;

    uniform sampler2D tCurrent;
    uniform sampler2D tNext;
    uniform vec2 uResolution;
    uniform vec2 uCurrentSize;
    uniform vec2 uNextSize;
    uniform float uProgress;
    uniform float uDir;
    uniform int uMode;
    uniform float uIntensity;
    uniform float uScale;
    uniform float uAberration;
    uniform float uDrift;
    uniform float uTime;
    uniform float uReduce;
    uniform vec2 uPointer;
    uniform vec3 uBgColor;

    varying vec2 vUv;

    const float PI = 3.14159265359;

    float hash11(float p) {
        p = fract(p * 0.1031);
        p *= p + 33.33;
        p *= p + p;
        return fract(p);
    }

    float hash21(vec2 p) {
        vec3 p3 = fract(vec3(p.xyx) * 0.1031);
        p3 += dot(p3, p3.yzx + 33.33);
        return fract((p3.x + p3.y) * p3.z);
    }

    float noise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        vec2 u = f * f * (3.0 - 2.0 * f);
        float a = hash21(i);
        float b = hash21(i + vec2(1.0, 0.0));
        float c = hash21(i + vec2(0.0, 1.0));
        float d = hash21(i + vec2(1.0, 1.0));
        return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
    }

    float fbm(vec2 p) {
        float v = 0.0;
        float a = 0.5;
        for (int i = 0; i < 5; i++) {
            v += a * noise(p);
            p *= 2.0;
            a *= 0.5;
        }
        return v;
    }

    mat2 rot(float a) {
        float s = sin(a);
        float c = cos(a);
        return mat2(c, -s, s, c);
    }

    // Zamieniona logika z 'cover' na 'contain'
    vec2 containUV(vec2 uv, vec2 res, vec2 img) {
        float rA = res.x / max(res.y, 1.0);
        float iA = img.x / max(img.y, 1.0);
        vec2 s = vec2(1.0);
        float ratio = rA / max(iA, 0.0001);
        if (ratio > 1.0) {
            s.x = ratio;
        } else {
            s.y = 1.0 / ratio;
        }
        return (uv - 0.5) * s + 0.5;
    }

    void main() {
        float p = clamp(uProgress, 0.0, 1.0);
        float env = sin(p * PI);

        vec2 uv = vUv;

        uv += vec2(sin(uTime * 0.25 + uv.y * 4.0), cos(uTime * 0.22 + uv.x * 4.0)) * uDrift * 0.008;
        uv = (uv - 0.5) * (1.0 - uDrift * 0.02 * sin(uTime * 0.4)) + 0.5;

        vec2 uvC = uv;
        vec2 uvN = uv;
        float m = smoothstep(0.0, 1.0, p);

        if (uReduce < 0.5) {
            if (uMode == 3) {
                vec2 c = uv - 0.5;
                float r = length(c);
                float ang = env * uIntensity * 3.5 * (1.0 - r);
                uvC = rot(ang) * c + 0.5;
                uvN = rot(-ang) * c + 0.5;
                m = smoothstep(0.0, 1.0, p);
            } else if (uMode == 1) {
                float d = distance(uv, uPointer);
                float ring = p * 1.6;
                float wave = sin((d - ring) * 30.0) * env;
                vec2 dir = normalize(uv - uPointer + 1e-4);
                vec2 disp = dir * wave * uIntensity * 0.25;
                uvC = uv + disp;
                uvN = uv + disp * 0.6;
                m = 1.0 - smoothstep(ring - 0.03, ring + 0.03, d);
            } else if (uMode == 2) {
                float slices = 14.0;
                float row = floor(uv.y * slices);
                float rnd = hash11(row);
                vec2 disp = vec2((rnd - 0.5) * env * uIntensity * 0.6, 0.0);
                uvC = uv + disp;
                uvN = uv + disp;
                float localX = uDir > 0.0 ? uv.x : 1.0 - uv.x;
                float th = p * 1.5 - 0.25 + (rnd - 0.5) * 0.25;
                m = 1.0 - smoothstep(th - 0.06, th + 0.06, localX);
            } else {
                float nn = fbm(uv * uScale + uTime * 0.03);
                float warp = fbm(uv * uScale * 1.7 - uTime * 0.02);
                vec2 g = vec2(nn, warp) - 0.5;
                uvC = uv + g * uIntensity * 0.5 * p;
                uvN = uv - g * uIntensity * 0.5 * (1.0 - p);
                m = smoothstep(nn - 0.15, nn + 0.15, p);
            }
        }

        vec2 sC = containUV(uvC, uResolution, uCurrentSize);
        vec2 sN = containUV(uvN, uResolution, uNextSize);

        float ca = uReduce < 0.5 ? uAberration * env * 0.03 : 0.0;

        bool oC = sC.x < 0.0 || sC.x > 1.0 || sC.y < 0.0 || sC.y > 1.0;
        bool oN = sN.x < 0.0 || sN.x > 1.0 || sN.y < 0.0 || sN.y > 1.0;

        vec4 texC_g = oC ? vec4(0.0) : texture2D(tCurrent, sC);
        vec4 texN_g = oN ? vec4(0.0) : texture2D(tNext, sN);

        vec2 sCr = sC + vec2(ca, 0.0);
        vec2 sCb = sC - vec2(ca, 0.0);
        float rC = (sCr.x < 0.0 || sCr.x > 1.0 || sCr.y < 0.0 || sCr.y > 1.0) ? 0.0 : texture2D(tCurrent, sCr).r;
        float bC = (sCb.x < 0.0 || sCb.x > 1.0 || sCb.y < 0.0 || sCb.y > 1.0) ? 0.0 : texture2D(tCurrent, sCb).b;

        vec2 sNr = sN + vec2(ca, 0.0);
        vec2 sNb = sN - vec2(ca, 0.0);
        float rN = (sNr.x < 0.0 || sNr.x > 1.0 || sNr.y < 0.0 || sNr.y > 1.0) ? 0.0 : texture2D(tNext, sNr).r;
        float bN = (sNb.x < 0.0 || sNb.x > 1.0 || sNb.y < 0.0 || sNb.y > 1.0) ? 0.0 : texture2D(tNext, sNb).b;

        vec3 colC = vec3(rC, texC_g.g, bC);
        vec3 colN = vec3(rN, texN_g.g, bN);

        vec3 texCol = mix(colC, colN, m);
        float texAlpha = mix(texC_g.a, texN_g.a, m);

        vec3 finalCol = mix(uBgColor, texCol, texAlpha);
        gl_FragColor = vec4(finalCol, 1.0);
    }`;

    function makeFallbackTexture(gl: any) {
        const size = 4;
        const data = new Uint8Array(size * size * 4);
        for (let i = 0; i < size * size; i++) {
            data[i * 4] = 24;
            data[i * 4 + 1] = 24;
            data[i * 4 + 2] = 28;
            data[i * 4 + 3] = 255;
        }
        return new Texture(gl, { image: data, width: size, height: size, generateMipmaps: false });
    }

    function hexToRgb(hex: string) {
        let h = (hex || '#000000').replace('#', '');
        if (h.length === 3) h = h.split('').map(c => c + c).join('');
        const n = parseInt(h, 16);
        return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
    }

    class MorphEngine {
        container: any; items: any[]; getOptions: any; onIndexChange: any; reducedMotion: any; current: any; animating: boolean; dragging: boolean; dragDir: number; shownIndex: any; tween: any; renderer: any; gl: any; canvas: any; geometry: any; textures: any[]; sizes: any[]; program: any; mesh: any; boundContextLost: any; resizeObserver: any; boundLoop: any; raf: any;
        constructor(container: any, { items, startIndex, reducedMotion, getOptions, onIndexChange, dprCap }: any) {
            this.container = container;
            this.items = items;
            this.getOptions = getOptions;
            this.onIndexChange = onIndexChange;
            this.reducedMotion = reducedMotion;

            this.current = startIndex;
            this.animating = false;
            this.dragging = false;
            this.dragDir = 0;
            this.shownIndex = startIndex;
            this.tween = null;

            this.renderer = new Renderer({
                alpha: true,
                antialias: true,
                dpr: Math.min(window.devicePixelRatio || 1, dprCap)
            });
            this.gl = this.renderer.gl;
            this.gl.clearColor(0.0, 0.0, 0.0, 0.0);

            this.canvas = this.gl.canvas;
            this.canvas.style.width = '100%';
            this.canvas.style.height = '100%';
            this.canvas.style.display = 'block';
            this.canvas.style.outline = 'none';
            container.appendChild(this.canvas);

            this.geometry = new Triangle(this.gl);

            this.textures = this.items.map(() => makeFallbackTexture(this.gl));
            this.sizes = this.items.map(() => [1, 1]);

            const opts = this.getOptions();
            this.program = new Program(this.gl, {
                vertex: vertexShader,
                fragment: fragmentShader,
                uniforms: {
                    tCurrent: { value: this.textures[this.current] },
                    tNext: { value: this.textures[this.current] },
                    uResolution: { value: [1, 1] },
                    uCurrentSize: { value: this.sizes[this.current] },
                    uNextSize: { value: this.sizes[this.current] },
                    uProgress: { value: 0 },
                    uDir: { value: 1 },
                    uMode: { value: TRANSITIONS[opts.transition] ?? 0 },
                    uIntensity: { value: opts.intensity },
                    uScale: { value: opts.scale },
                    uAberration: { value: opts.aberration },
                    uDrift: { value: opts.drift },
                    uTime: { value: 0 },
                    uReduce: { value: reducedMotion ? 1 : 0 },
                    uPointer: { value: [0.5, 0.5] },
                    uBgColor: { value: hexToRgb(opts.bgColor) }
                }
            });

            this.mesh = new Mesh(this.gl, { geometry: this.geometry, program: this.program });

            this.boundContextLost = this.onContextLost.bind(this);
            this.canvas.addEventListener('webglcontextlost', this.boundContextLost, false);

            this.resizeObserver = new ResizeObserver(() => this.resize());
            this.resizeObserver.observe(container);
            this.resize();

            this.loadTextures();

            this.boundLoop = this.loop.bind(this);
            this.raf = requestAnimationFrame(this.boundLoop);
        }

        updateTextures(newUrls: string[]) {
            this.items = newUrls;
            this.loadTextures();
        }

        loadTextures() {
            this.items.forEach((src, index) => {
                const img = new Image();
                img.crossOrigin = 'anonymous';
                img.src = src;
                img.onload = () => {
                    const texture = new Texture(this.gl, { generateMipmaps: false });
                    texture.image = img;
                    this.textures[index] = texture;
                    this.sizes[index] = [img.naturalWidth || 1, img.naturalHeight || 1];
                    if (index === this.current) {
                        this.program.uniforms.tCurrent.value = texture;
                        this.program.uniforms.uCurrentSize.value = this.sizes[index];
                    }
                };
            });
        }

        resize() {
            const rect = this.container.getBoundingClientRect();
            const w = Math.max(rect.width, 1);
            const h = Math.max(rect.height, 1);
            this.renderer.setSize(w, h);
            this.program.uniforms.uResolution.value = [this.gl.canvas.width, this.gl.canvas.height];
        }

        syncOptions() {
            const opts = this.getOptions();
            this.program.uniforms.uMode.value = TRANSITIONS[opts.transition] ?? 0;
            this.program.uniforms.uIntensity.value = opts.intensity;
            this.program.uniforms.uScale.value = opts.scale;
            this.program.uniforms.uAberration.value = opts.aberration;
            this.program.uniforms.uDrift.value = opts.drift;
            this.program.uniforms.uBgColor.value = hexToRgb(opts.bgColor);
        }

        loop(t: number) {
            this.program.uniforms.uTime.value = t * 0.001;
            if (!this.dragging && !this.animating) this.syncOptions();
            this.renderer.render({ scene: this.mesh });
            this.raf = requestAnimationFrame(this.boundLoop);
        }

        wrap(i: number) {
            const n = this.items.length;
            return ((i % n) + n) % n;
        }

        prepareNext(dir: number) {
            const target = this.wrap(this.current + dir);
            this.program.uniforms.tCurrent.value = this.textures[this.current];
            this.program.uniforms.uCurrentSize.value = this.sizes[this.current];
            this.program.uniforms.tNext.value = this.textures[target];
            this.program.uniforms.uNextSize.value = this.sizes[target];
            this.program.uniforms.uDir.value = dir;
            return target;
        }

        goTo(dir: number) {
            if (this.animating || this.dragging || this.items.length < 2) return;
            const opts = this.getOptions();
            if (!opts.loop) {
                const raw = this.current + dir;
                if (raw < 0 || raw > this.items.length - 1) return;
            }
            this.syncOptions();
            const target = this.prepareNext(dir);
            this.animating = true;
            this.announce(target);
            const duration = this.reducedMotion ? Math.min(opts.duration, 0.4) : opts.duration;
            this.tween = gsap.fromTo(
                this.program.uniforms.uProgress,
                { value: 0 },
                { value: 1, duration, ease: opts.ease, onComplete: () => this.commit(target) }
            );
        }

        announce(index: number) {
            if (index === this.shownIndex) return;
            this.shownIndex = index;
            if (this.onIndexChange) this.onIndexChange(index);
        }

        commit(target: number) {
            this.current = target;
            this.program.uniforms.tCurrent.value = this.textures[target];
            this.program.uniforms.uCurrentSize.value = this.sizes[target];
            this.program.uniforms.uProgress.value = 0;
            this.animating = false;
            this.tween = null;
            this.announce(target);
        }

        next() { this.goTo(1); }
        prev() { this.goTo(-1); }

        setPointer(x: number, y: number) {
            this.program.uniforms.uPointer.value = [x, y];
        }

        beginDrag() {
            if (this.animating || this.items.length < 2) return false;
            this.dragging = true;
            this.dragDir = 0;
            this.syncOptions();
            return true;
        }

        drag(ndx: number) {
            if (!this.dragging) return;
            const opts = this.getOptions();
            const dir = ndx < 0 ? 1 : -1;
            if (!opts.loop) {
                const raw = this.current + dir;
                if (raw < 0 || raw > this.items.length - 1) {
                    this.program.uniforms.uProgress.value = 0;
                    return;
                }
            }
            if (dir !== this.dragDir) {
                this.dragDir = dir;
                this.prepareNext(dir);
            }
            const progress = Math.min(Math.abs(ndx), 1);
            this.program.uniforms.uProgress.value = progress;
            this.announce(progress > 0.5 ? this.wrap(this.current + dir) : this.current);
        }

        endDrag() {
            if (!this.dragging) return;
            this.dragging = false;
            const p = this.program.uniforms.uProgress.value;
            if (this.dragDir === 0) return;
            const target = this.wrap(this.current + this.dragDir);
            const duration = this.reducedMotion ? 0.3 : 0.5;
            this.animating = true;
            if (p > 0.4) {
                this.announce(target);
                this.tween = gsap.to(this.program.uniforms.uProgress, {
                    value: 1, duration, ease: 'power2.out', onComplete: () => this.commit(target)
                });
            } else {
                this.announce(this.current);
                this.tween = gsap.to(this.program.uniforms.uProgress, {
                    value: 0, duration, ease: 'power2.out', onComplete: () => {
                        this.animating = false;
                        this.tween = null;
                    }
                });
            }
        }

        onContextLost(e: Event) {
            e.preventDefault();
            cancelAnimationFrame(this.raf);
        }

        destroy() {
            cancelAnimationFrame(this.raf);
            if (this.tween) this.tween.kill();
            this.resizeObserver.disconnect();
            this.canvas.removeEventListener('webglcontextlost', this.boundContextLost);
            if (this.program && this.program.program) this.gl.deleteProgram(this.program.program);
            const ext = this.gl.getExtension('WEBGL_lose_context');
            if (ext) ext.loseContext();
            if (this.canvas.parentNode) this.canvas.parentNode.removeChild(this.canvas);
        }
    }

    function initMorph(node: HTMLElement) {
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        engine = new MorphEngine(node, {
            items: features.map(f => isLightMode ? f.imgLight : f.imgDark),
            startIndex: activeFeature,
            reducedMotion,
            dprCap: 2,
            getOptions: () => ({
                transition: 'melt',
                duration: 1.1,
                ease: 'power2.inOut',
                intensity: 0.55,
                scale: 2.4,
                aberration: 0.35,
                drift: 0.4,
                bgColor: isLightMode ? '#ffffff' : '#111111',
                loop: true
            }),
            onIndexChange: (idx: number) => {
                activeFeature = idx;
            }
        });

        return {
            destroy() {
                if (engine) {
                    engine.destroy();
                    engine = null;
                }
            }
        };
    }

    function nextFeature() {
        if (engine) engine.next();
        else activeFeature = (activeFeature + 1) % features.length;
    }

    function prevFeature() {
        if (engine) engine.prev();
        else activeFeature = (activeFeature - 1 + features.length) % features.length;
    }

    function toggleFaq(index: number) {
        openFaqIndex = openFaqIndex === index ? null : index;
    }

    $: {
        const hash = $page.url.hash.replace('#', '');
        if (hash === 'jak-to-dziala' || hash === 'o-wa-gone' || hash === 'kontakt') {
            currentView = hash as ViewSection;
        } else {
            currentView = 'jak-to-dziala';
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (currentView === 'o-wa-gone') {
            if (e.key === 'ArrowRight') nextFeature();
            if (e.key === 'ArrowLeft') prevFeature();
        }
    }

    function handlePointerDown(e: PointerEvent) {
        if (!morphContainer || !engine) return;
        const rect = morphContainer.getBoundingClientRect();
        dragWidth = rect.width || 1;
        startX = e.clientX;
        const px = (e.clientX - rect.left) / rect.width;
        const py = (e.clientY - rect.top) / rect.height;
        engine.setPointer(px, 1 - py);
        activeDrag = engine.beginDrag();
        if (activeDrag && morphContainer.setPointerCapture) {
            try { morphContainer.setPointerCapture(e.pointerId); } catch {}
        }
    }

    function handlePointerMove(e: PointerEvent) {
        if (!activeDrag || !engine) return;
        const ndx = (e.clientX - startX) / dragWidth;
        engine.drag(ndx);
    }

    function handlePointerUp(e: PointerEvent) {
        if (!activeDrag || !engine) return;
        activeDrag = false;
        engine.endDrag();
    }

    onMount(() => {
        window.addEventListener('keydown', handleKeydown);
        
        isLightMode = document.documentElement.classList.contains('light-mode');
        
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    isLightMode = document.documentElement.classList.contains('light-mode');
                }
            });
        });
        observer.observe(document.documentElement, { attributes: true });

        if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
            const updateCursor = (event: PointerEvent) => {
                cursorX = event.clientX;
                cursorY = event.clientY;
                cursorVisible = true;
                cursorHover =
                    event.target instanceof Element &&
                    Boolean(event.target.closest('a, button, input, textarea, .faq-head, .slider-arrow, .morph-container'));
            };
            const hideCursor = () => (cursorVisible = false);

            document.documentElement.classList.add('dot-cursor');
            window.addEventListener('pointermove', updateCursor);
            window.addEventListener('mouseleave', hideCursor);

            return () => {
                window.removeEventListener('keydown', handleKeydown);
                observer.disconnect();
                
                document.documentElement.classList.remove('dot-cursor');
                window.removeEventListener('pointermove', updateCursor);
                window.removeEventListener('mouseleave', hideCursor);
            };
        }

        return () => {
            window.removeEventListener('keydown', handleKeydown);
            observer.disconnect();
        };
    });

    $: currentImages = features.map(f => isLightMode ? f.imgLight : f.imgDark);
    $: if (engine && currentImages) {
        engine.updateTextures(currentImages);
        engine.syncOptions();
    }

    let showAuthModal = false;
    let isClosingAuthModal = false;
    let authMode: 'login' | 'register' = 'login';
    let triggerElement: HTMLElement | null = null;
    let modalElement: HTMLElement | null = null;

    async function openAuthModal(mode: 'login' | 'register' = 'login', e?: CustomEvent | MouseEvent) {
        if (e && 'preventDefault' in e && typeof e.preventDefault === 'function') {
            e.preventDefault();
        }
        if (e && 'currentTarget' in e && e.currentTarget) {
            triggerElement = e.currentTarget as HTMLElement;
        } else {
            triggerElement = document.activeElement as HTMLElement;
        }
        authMode = mode;
        isClosingAuthModal = false;
        showAuthModal = true;
        await tick();
        const closeBtn = modalElement?.querySelector<HTMLButtonElement>('.modal-close');
        closeBtn?.focus();
    }

    function closeAuthModal() {
        if (!showAuthModal || isClosingAuthModal) return;
        isClosingAuthModal = true;
        setTimeout(() => {
            showAuthModal = false;
            isClosingAuthModal = false;
            triggerElement?.focus();
        }, 250);
    }

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) closeAuthModal();
    }

    function handleModalKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') {
            e.stopPropagation();
            closeAuthModal();
        }
    }

    let contactName = '';
    let contactEmail = '';
    let contactMessage = '';
    let nameTouched = false;
    let emailTouched = false;
    let messageTouched = false;
    let formSubmittedAttempt = false;
    let formStatus: 'idle' | 'submitting' | 'success' | 'error' = 'idle';

    $: isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contactEmail.trim());
    $: isNameValid = contactName.trim().length >= 2;
    $: isMessageValid = contactMessage.trim().length >= 6;

    $: showNameError = (nameTouched || formSubmittedAttempt) && !isNameValid;
    $: showEmailError = (emailTouched || formSubmittedAttempt) && !isEmailValid;
    $: showMessageError = (messageTouched || formSubmittedAttempt) && !isMessageValid;

    function handleSubmitContact(event: SubmitEvent) {
        event.preventDefault();
        formSubmittedAttempt = true;

        if (!isNameValid || !isEmailValid || !isMessageValid) {
            formStatus = 'error';
            return;
        }

        formStatus = 'submitting';
        setTimeout(() => {
            formStatus = 'success';
            contactName = '';
            contactEmail = '';
            contactMessage = '';
            nameTouched = false;
            emailTouched = false;
            messageTouched = false;
            formSubmittedAttempt = false;
            setTimeout(() => {
                if (formStatus === 'success') formStatus = 'idle';
            }, 4500);
        }, 800);
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
    <title>{$t('landing.head.title')}</title>
</svelte:head>

<div class="landing-viewport">
    <div
        class="custom-cursor"
        class:is-visible={cursorVisible}
        style="--cursor-x: {cursorX}px; --cursor-y: {cursorY}px"
        aria-hidden="true"
    >
        <span class="cursor-dot" class:is-hovering={cursorHover}></span>
    </div>

    <PublicNav authenticated={data.authenticated} on:openLogin={() => openAuthModal('login')} />

    <main class="viewport-stage" class:is-hero={currentView === 'jak-to-dziala'} aria-hidden={showAuthModal}>
        {#if currentView === 'jak-to-dziala'}
            <section class="screen-view hero-screen">
                <div class="hero-shape-container">
                    <ShapeWaves
                        text="WA.GONE"
                        fontFamily='"Inter Variable", Inter, sans-serif'
                        fontWeight={500}
                        textSize={0.6}
                        shapes="circles"
                        cellSize={8}
                        dotSize={0.84}
                        color={isLightMode ? "#94a3b8" : "#929292"}
                        hoverColor={isLightMode ? "#111827" : "#ffffff"}
                        backgroundColor={isLightMode ? "#f4f5f3" : "#141414"}
                        speed={2}
                        scale={0.55}
                        contrast={1.65}
                        brightness={0.38}
                        flow={3}
                        direction={215}
                        fade={0.22}
                        interactive={true}
                        splashRadius={16}
                        splashStrength={0.6}
                        glow={0}
                        intro={true}
                        introDuration={1.6}
                        paused={false}
                    />
                </div>
            </section>
        {:else if currentView === 'o-wa-gone'}
            <section class="screen-view about-screen">
                <div class="about-grid">
                    <div class="faq-column">
                        <h2 class="column-title">FAQ</h2>
                        <div class="faq-accordion">
                            {#each faqItems as item, idx}
                                <div class="faq-card" class:is-expanded={openFaqIndex === idx}>
                                    <button 
                                        type="button" 
                                        class="faq-head" 
                                        on:click={() => toggleFaq(idx)}
                                        aria-expanded={openFaqIndex === idx}
                                    >
                                        <span>{item.question}</span>
                                    </button>
                                    {#if openFaqIndex === idx}
                                        <div 
                                            class="faq-body" 
                                            transition:slide={{ duration: 250, easing: cubicOut }}
                                        >
                                            <p>{item.answer}</p>
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    </div>

                    <div class="features-column">
                        <div class="feature-card">
                            <div 
                                class="illustration-container morph-container" 
                                bind:this={morphContainer}
                                use:initMorph
                                on:pointerdown={handlePointerDown}
                                on:pointermove={handlePointerMove}
                                on:pointerup={handlePointerUp}
                                on:pointercancel={handlePointerUp}
                                style="touch-action: pan-y;"
                            >
                            </div>
                            
                            <div class="feature-footer">
                                <p class="feature-desc">
                                    <strong>{displayedTag}</strong>{displayedCopy}<span class="cursor" aria-hidden="true">|</span>
                                </p>
                            </div>

                            <button 
                                type="button" 
                                class="slider-arrow next-btn" 
                                on:click={nextFeature}
                                aria-label="Następna funkcja"
                                title="Następna funkcja"
                            >
                                <span class="dot-indicator"></span>
                            </button>
                        </div>
                    </div>
                </div>
            </section>
        {:else if currentView === 'kontakt'}
            <section class="screen-view contact-screen">
                <div class="contact-card">
                    <h2 class="column-title">KONTAKT</h2>
                    <form class="contact-form" on:submit={handleSubmitContact} novalidate>
                        <div class="form-row">
                            <div class="field-wrap">
                                <input
                                    type="text"
                                    class:is-error={showNameError}
                                    bind:value={contactName}
                                    on:blur={() => (nameTouched = true)}
                                    placeholder={$t('landing.contact.namePlaceholder')}
                                    aria-invalid={showNameError ? 'true' : undefined}
                                />
                                {#if showNameError}
                                    <span class="field-hint" role="alert">Wpisz min. 2 znaki</span>
                                {/if}
                            </div>

                            <div class="field-wrap">
                                <input
                                    type="email"
                                    class:is-error={showEmailError}
                                    bind:value={contactEmail}
                                    on:blur={() => (emailTouched = true)}
                                    placeholder={$t('landing.contact.emailPlaceholder')}
                                    aria-invalid={showEmailError ? 'true' : undefined}
                                />
                                {#if showEmailError}
                                    <span class="field-hint" role="alert">Wprowadź poprawny adres e-mail.</span>
                                {/if}
                            </div>
                        </div>

                        <div class="field-wrap">
                            <textarea
                                rows="12"
                                class:is-error={showMessageError}
                                bind:value={contactMessage}
                                on:blur={() => (messageTouched = true)}
                                placeholder={$t('landing.contact.messagePlaceholder')}
                                aria-invalid={showMessageError ? 'true' : undefined}
                            ></textarea>
                            {#if showMessageError}
                                <span class="field-hint" role="alert">Wiadomość musi mieć min. 6 znaków</span>
                            {/if}
                        </div>

                        <div class="form-bottom-row">
                            <div class="feedback-area">
                                {#if formStatus === 'success'}
                                    <span class="feedback-msg success" role="status">
                                        <span class="material-symbols-outlined icon-status">check_circle</span>
                                        {$t('landing.contact.success')}
                                    </span>
                                {:else if formStatus === 'error' && (showNameError || showEmailError || showMessageError)}
                                    <span class="feedback-msg error" role="alert">
                                        <span class="material-symbols-outlined icon-status">error</span>
                                        Uzupełnij poprawnie wszystkie pola
                                    </span>
                                {/if}
                            </div>

                            <button 
                                type="submit" 
                                class="cta-submit" 
                                disabled={formStatus === 'submitting'}
                            >
                                {formStatus === 'submitting' ? 'WYSYŁANIE...' : 'WYŚLIJ WIADOMOŚĆ'}
                            </button>
                        </div>
                    </form>
                </div>
            </section>
        {/if}
    </main>

    <footer class="bottom-bar">
        <span>WA.GONE @2026</span>
    </footer>

    {#if showAuthModal}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div
            class="modal-backdrop"
            class:is-closing={isClosingAuthModal}
            role="dialog"
            tabindex="-1"
            aria-modal="true"
            aria-label={authMode === 'login' ? 'Logowanie' : 'Rejestracja'}
            bind:this={modalElement}
            on:click={handleBackdropClick}
            on:keydown={handleModalKeydown}
        >
            <div class="modal-card">
                <button
                    class="modal-close"
                    type="button"
                    on:click={closeAuthModal}
                    title="Zamknij"
                    aria-label="Zamknij"
                >
                    <span class="material-symbols-outlined" aria-hidden="true">close</span>
                </button>
                <AuthCard mode={authMode} error={form?.error} email={form?.email ?? ''} />
            </div>
        </div>
    {/if}
</div>

<style>
    :global(:root) {
        --viewport-bg: #141414;
        --card-bg: #111111;
        --text-primary: #f5f7f8;
        --text-muted: #838a90;
        --text-heading: #9ea4aa;
        --text-strong: #cfd4d8;
        --input-bg: #0d0d0d;
        --btn-submit-bg: #f3eee7;
        --btn-submit-color: #111111;
        --dot-bg: #e2e2de;
        --footer-color: #4f555b;
        --focus-ring: rgba(255, 255, 255, 0.65);
        --error-color: #de8489;
        --success-color: #6cb09f;
        --backdrop-bg: rgba(0, 0, 0, 0.75);
    }

    :global(html.light-mode) {
        --viewport-bg: #f4f5f3;
        --card-bg: #ffffff;
        --text-primary: #111827;
        --text-muted: #52606a;
        --text-heading: #374151;
        --text-strong: #1f2937;
        --input-bg: #eaedea;
        --btn-submit-bg: #111827;
        --btn-submit-color: #ffffff;
        --dot-bg: #111827;
        --footer-color: #94a3b8;
        --focus-ring: rgba(17, 24, 39, 0.65);
        --error-color: #c95158;
        --success-color: #2e8570;
        --backdrop-bg: rgba(0, 0, 0, 0.4);
    }

    :global(html) {
        scrollbar-width: none;
    }
    :global(html::-webkit-scrollbar) {
        display: none;
    }

    :global(html.dot-cursor *:not(input):not(textarea)) {
        cursor: none !important;
    }

    .custom-cursor {
        position: fixed;
        top: 0;
        left: 0;
        width: 0;
        height: 0;
        z-index: 9999;
        opacity: 0;
        pointer-events: none;
        transform: translate3d(var(--cursor-x), var(--cursor-y), 0);
        transition: opacity 150ms ease;
        will-change: transform;
    }

    .custom-cursor.is-visible {
        opacity: 1;
    }

    .cursor-dot {
        display: block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #ffffff;
        transform: translate(-50%, -50%) scale(1);
        transition: transform 200ms cubic-bezier(0.16, 1, 0.3, 1), background-color 200ms ease, border-color 200ms ease;
    }

    :global(html.light-mode) .cursor-dot {
        background: #111111;
    }

    .cursor-dot.is-hovering {
        transform: translate(-50%, -50%) scale(4);
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.4);
    }

    :global(html.light-mode) .cursor-dot.is-hovering {
        background: rgba(17, 17, 17, 0.1);
        border: 1px solid rgba(17, 17, 17, 0.3);
    }

    :global(html, body) {
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden !important;
        background-color: var(--viewport-bg);
        color: var(--text-primary);
        font-family: 'Inter Variable', Inter, sans-serif;
        transition: background-color 200ms ease, color 200ms ease;
    }

    .landing-viewport {
        position: relative;
        width: 100vw;
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: var(--viewport-bg);
        box-sizing: border-box;
        overflow: hidden;
        transition: background-color 200ms ease;
    }

    .viewport-stage {
        flex: 1;
        position: relative;
        width: 100%;
        max-width: 1440px;
        margin: 0 auto;
        padding: 0 clamp(20px, 4vw, 56px);
        box-sizing: border-box;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        transition: max-width 300ms ease, padding 300ms ease;
    }

    .viewport-stage.is-hero {
        max-width: 100%;
        padding: 0;
    }

    .screen-view {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .hero-screen {
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    .hero-shape-container {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
    }

    .about-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 40px;
        width: 100%;
        max-height: 80vh;
        align-items: center;
    }

    .column-title {
        font-size: 0.82rem;
        font-weight: 500;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--text-heading);
        margin: 0 0 24px;
        text-align: center;
    }

    .faq-column {
        display: flex;
        flex-direction: column;
        height: 520px;
    }

    .faq-accordion {
        display: flex;
        flex-direction: column;
        gap: 10px;
        overflow-y: auto;
        padding-right: 6px;
    }

    .faq-card {
        background: var(--card-bg);
        border-radius: 12px;
        border: 0;
        box-shadow: none;
        overflow: hidden;
        transition: background-color 200ms ease;
    }

    .faq-head {
        width: 100%;
        background: none;
        border: 0;
        color: var(--text-strong);
        padding: 16px 20px;
        text-align: left;
        font-size: 0.85rem;
        font-family: inherit;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 12px;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .faq-head:focus {
        outline: none;
    }

    .faq-head:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: -2px;
        border-radius: 10px;
    }

    .faq-head:hover {
        color: var(--text-primary);
    }

    .faq-body {
        padding: 0 20px 18px;
    }

    .faq-body p {
        margin: 0;
        font-size: 0.8rem;
        line-height: 1.55;
        color: var(--text-muted);
    }

    .features-column {
        height: 520px;
        display: flex;
        align-items: center;
    }

    .feature-card {
        position: relative;
        width: 100%;
        height: 100%;
        background: var(--card-bg);
        border-radius: 14px;
        border: 0;
        box-shadow: none;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: space-between;
        padding: 32px 36px;
        box-sizing: border-box;
        transition: background-color 200ms ease;
    }

    .illustration-container {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        overflow: hidden;
    }

    .feature-footer {
        width: 100%;
        margin-top: 16px;
        min-height: 48px;
    }

    .feature-desc {
        margin: 0;
        font-size: 0.85rem;
        line-height: 1.5;
        color: var(--text-muted);
    }

    .feature-desc strong {
        color: var(--text-strong);
        font-weight: 500;
    }

    .cursor {
        display: inline-block;
        width: 2px;
        margin-left: 2px;
        vertical-align: text-bottom;
        color: var(--text-strong);
        animation: blink 1s step-end infinite;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
    }

    .slider-arrow {
        position: absolute;
        top: 50%;
        right: 18px;
        transform: translateY(-50%);
        background: none;
        border: 0;
        padding: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: opacity 150ms ease;
    }

    .slider-arrow:focus {
        outline: none;
    }

    .slider-arrow:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .slider-arrow:hover {
        opacity: 0.75;
    }

    .dot-indicator {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--dot-bg);
        transition: background-color 200ms ease, transform 150ms ease;
    }

    .slider-arrow:hover .dot-indicator {
        transform: scale(1.15);
    }

    .contact-card {
        width: 100%;
        max-width: 600px;
        box-sizing: border-box;
    }

    .contact-form {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    .field-wrap {
        display: flex;
        flex-direction: column;
        gap: 4px;
        width: 100%;
    }

    .contact-form input,
    .contact-form textarea {
        width: 100%;
        padding: 16px 20px;
        border-radius: 12px;
        border: 0 !important;
        box-shadow: none !important;
        background: var(--input-bg);
        color: var(--text-primary);
        font-family: inherit;
        font-size: 0.88rem;
        box-sizing: border-box;
        transition: background-color 200ms ease, color 200ms ease;
    }

    .contact-form textarea {
        resize: none;
        min-height: 240px;
    }

    .contact-form input.is-error,
    .contact-form textarea.is-error {
        background: rgba(222, 132, 137, 0.12) !important;
        color: #de8489 !important;
        border: 0 !important;
        box-shadow: none !important;
    }

    :global(html.light-mode) .contact-form input.is-error,
    :global(html.light-mode) .contact-form textarea.is-error {
        background: rgba(201, 81, 88, 0.12) !important;
        color: #c95158 !important;
    }

    .contact-form input:focus,
    .contact-form textarea:focus {
        outline: none;
    }

    .contact-form input:focus-visible,
    .contact-form textarea:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .contact-form input.is-error:focus-visible,
    .contact-form textarea.is-error:focus-visible {
        outline-color: rgba(222, 132, 137, 0.65);
    }

    :global(html.light-mode) .contact-form input.is-error:focus-visible,
    :global(html.light-mode) .contact-form textarea.is-error:focus-visible {
        outline-color: rgba(201, 81, 88, 0.65);
    }

    .field-hint {
        font-size: 0.72rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #de8489;
        padding-left: 4px;
        margin-top: 4px;
        font-weight: 400;
    }

    :global(html.light-mode) .field-hint {
        color: #c95158;
    }

    .form-bottom-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 6px;
        gap: 16px;
    }

    .feedback-area {
        flex: 1;
        min-width: 0;
    }

    .feedback-msg {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.76rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-weight: 500;
    }

    .feedback-msg.success {
        color: var(--success-color);
    }

    .feedback-msg.error {
        color: var(--error-color);
    }

    .icon-status {
        font-size: 16px;
    }

    .cta-submit {
        background: var(--btn-submit-bg);
        color: var(--btn-submit-color);
        border: 0;
        box-shadow: none;
        border-radius: 10px;
        padding: 14px 28px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        cursor: pointer;
        font-family: inherit;
        white-space: nowrap;
        transition: opacity 150ms ease, background-color 200ms ease, color 200ms ease;
    }

    .cta-submit:focus {
        outline: none;
    }

    .cta-submit:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .cta-submit:hover:not(:disabled) {
        opacity: 0.88;
    }

    .cta-submit:disabled {
        opacity: 0.5;
    }

    .bottom-bar {
        padding: 18px 44px;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 0.68rem;
        letter-spacing: 0.1em;
        color: var(--footer-color);
        flex-shrink: 0;
        transition: color 200ms ease;
    }

    .modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 200;
        background: var(--backdrop-bg);
        backdrop-filter: blur(6px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        outline: none;
    }

    .modal-card {
        position: relative;
        width: 100%;
        max-width: 440px;
    }

    .modal-close {
        position: absolute;
        top: 18px;
        right: 28px;
        z-index: 20;
        background: none;
        border: 0;
        color: var(--text-muted);
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        cursor: pointer;
        transition: opacity 150ms ease, color 150ms ease;
    }

    .modal-close:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
        border-radius: 6px;
    }

    .modal-close:hover {
        color: var(--text-primary);
    }

    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 20px;
        line-height: 1;
        display: inline-block;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        font-feature-settings: 'liga';
        user-select: none;
    }

    @media (max-width: 900px) {
        .about-grid {
            grid-template-columns: 1fr;
            max-height: none;
            overflow-y: auto;
        }

        .features-column,
        .faq-column {
            height: auto;
        }

        .form-row {
            grid-template-columns: 1fr;
        }
    }
</style>