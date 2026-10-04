/**
 * AeroQuantum-Wind — Real-Time Wind Flow & Aerodynamic Simulation Engine (wind-fx.js)
 *
 * Implements:
 * 1. 200-particle canvas streak flow in wind direction with upwind respawning,
 *    wake cone deficit deceleration, turbulent jitter, and dynamic 60fps governor.
 * 2. 3-blade aerodynamic rotor simulation rotating at speed ∝ effective_mps.
 * 3. Jensen expanding wake cones (k=0.075) with additive blending & deficit gradients.
 * 4. Draggable Before/After wipe split comparing baseline vs QAOA layouts.
 */

(function (window) {
    'use strict';

    class WindSimulationEngine {
        constructor() {
            this.canvas = null;
            this.ctx = null;
            this.map = null;

            // Flow & Physics State
            this.windAngle = 270.0; // Compass degrees
            this.windSpeed = 8.42;  // m/s freestream
            this.targetParticleCount = 200;
            this.activeParticleCount = 200;
            this.particles = [];

            // Layouts for Before/After Wipe
            this.qaoaLayout = [];
            this.baselineLayout = [];
            this.activeLayout = [];
            this.rotorStates = new Map(); // id -> { angle, speed, effectiveSpeed, isWaked }

            // Wipe Split State
            this.wipeProgress = 1.0; // 0.0 = 100% Baseline, 0.5 = Split 50/50, 1.0 = 100% QAOA
            this.isSplitWipe = false;
            this.splitX = 0; // Screen pixel X for divider

            // Visualization Toggles
            this.showParticles = true;
            this.showWakes = true;
            this.showRotors = true;

            // Frame Rate & Dynamic Governor
            this.isRunning = false;
            this.lastFrameTime = performance.now();
            this.avgFrameTime = 16.6;
            this.animFrameId = null;

            // Bind loops
            this.render = this.render.bind(this);
            this.handleResize = this.handleResize.bind(this);
        }

        init(canvasElem, leafletMap) {
            this.canvas = canvasElem;
            this.ctx = this.canvas.getContext('2d');
            this.map = leafletMap;

            this.handleResize();
            this.initParticles(this.targetParticleCount);

            window.addEventListener('resize', this.handleResize);
            if (this.map) {
                this.map.on('move', this.handleResize);
                this.map.on('zoom', this.handleResize);
                this.map.on('resize', this.handleResize);
            }

            this.start();
        }

        handleResize() {
            if (!this.canvas) return;
            const dpr = window.devicePixelRatio || 1;
            const parent = this.canvas.parentElement;
            const w = (parent && parent.clientWidth > 0) ? parent.clientWidth : window.innerWidth;
            const h = (parent && parent.clientHeight > 0) ? parent.clientHeight : window.innerHeight;

            this.canvas.width = w * dpr;
            this.canvas.height = h * dpr;
            this.canvas.style.width = w + 'px';
            this.canvas.style.height = h + 'px';
            this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            // Re-calculate split X pixel
            this.splitX = w * this.wipeProgress;
        }

        setWindAngle(deg) {
            this.windAngle = (deg % 360 + 360) % 360;
            this.updateRotorSpeeds();
        }

        setLayouts(qaoa, baseline) {
            this.qaoaLayout = Array.isArray(qaoa) ? qaoa : [];
            this.baselineLayout = Array.isArray(baseline) ? baseline : [];
            this.updateActiveLayout();
            this.updateRotorSpeeds();
        }

        setWipeProgress(progress, isSplit = false) {
            this.wipeProgress = Math.max(0.0, Math.min(1.0, progress));
            this.isSplitWipe = isSplit;
            this.splitX = window.innerWidth * this.wipeProgress;
            this.updateActiveLayout();
        }

        updateActiveLayout() {
            if (!this.isSplitWipe) {
                this.activeLayout = this.wipeProgress >= 0.5 ? this.qaoaLayout : this.baselineLayout;
            } else {
                // In split wipe mode, both layouts are rendered clipped left/right
                this.activeLayout = this.qaoaLayout;
            }
        }

        updateRotorSpeeds() {
            const allTurbines = [...this.qaoaLayout, ...this.baselineLayout];
            allTurbines.forEach((t) => {
                const effSpeed = typeof t.effective_mps === 'number' ? t.effective_mps : this.windSpeed;
                const isWaked = effSpeed < (this.windSpeed - 0.2);

                // Angular velocity: 8.42 m/s -> ~15 RPM visual (~0.045 rad/frame at 60fps)
                // Waked turbines spin visibly slower proportional to effective wind speed
                const speedRad = (effSpeed / this.windSpeed) * 0.045;

                const existing = this.rotorStates.get(t.id);
                if (existing) {
                    existing.speed = speedRad;
                    existing.effectiveSpeed = effSpeed;
                    existing.isWaked = isWaked;
                } else {
                    this.rotorStates.set(t.id, {
                        angle: Math.random() * Math.PI * 2,
                        speed: speedRad,
                        effectiveSpeed: effSpeed,
                        isWaked: isWaked
                    });
                }
            });
        }

        setToggles(toggles) {
            if ('showParticles' in toggles) this.showParticles = !!toggles.showParticles;
            if ('showWakes' in toggles) this.showWakes = !!toggles.showWakes;
            if ('showRotors' in toggles) this.showRotors = !!toggles.showRotors;
        }

        initParticles(count) {
            this.particles = [];
            const w = window.innerWidth;
            const h = window.innerHeight;

            for (let i = 0; i < count; i++) {
                this.particles.push(this.createRandomParticle(w, h));
            }
        }

        createRandomParticle(w, h) {
            return {
                x: Math.random() * w,
                y: Math.random() * h,
                speed: 1.8 + Math.random() * 2.2,
                length: 16 + Math.random() * 24,
                alpha: 0.25 + Math.random() * 0.45,
                age: Math.random() * 120,
                maxAge: 120 + Math.random() * 80,
                lateralOffset: 0,
                inWake: false,
                deficit: 0.0
            };
        }

        respawnParticleUpwind(p, w, h, wx, wy) {
            // Respawn along the perimeter edge facing upwind
            // Normal perpendicular to wind direction
            const nx = -wy;
            const ny = wx;

            // Random position along cross-section perpendicular to wind
            const maxDimension = Math.hypot(w, h);
            const lateral = (Math.random() - 0.5) * maxDimension * 1.5;
            const screenCenterX = w / 2;
            const screenCenterY = h / 2;

            // Offset backwards upwind by half diagonal
            const upwindDist = (maxDimension / 2) + 60;
            p.x = screenCenterX - wx * upwindDist + nx * lateral;
            p.y = screenCenterY - wy * upwindDist + ny * lateral;

            p.speed = 1.8 + Math.random() * 2.2;
            p.length = 16 + Math.random() * 24;
            p.alpha = 0.25 + Math.random() * 0.45;
            p.age = 0;
            p.maxAge = 140 + Math.random() * 80;
            p.lateralOffset = 0;
            p.inWake = false;
            p.deficit = 0.0;
        }

        start() {
            if (this.isRunning) return;
            this.isRunning = true;
            this.lastFrameTime = performance.now();
            this.animFrameId = requestAnimationFrame(this.render);
        }

        stop() {
            this.isRunning = false;
            if (this.animFrameId) {
                cancelAnimationFrame(this.animFrameId);
                this.animFrameId = null;
            }
        }

        render(timestamp) {
            if (!this.isRunning) return;

            // Frame time monitoring for 60fps target
            const dt = timestamp - this.lastFrameTime;
            this.lastFrameTime = timestamp;
            if (dt > 0 && dt < 200) {
                this.avgFrameTime = this.avgFrameTime * 0.9 + dt * 0.1;
                // If frame time > 25ms (<40fps), dynamically reduce particle count
                if (this.avgFrameTime > 25.0 && this.activeParticleCount > 70) {
                    this.activeParticleCount = Math.max(60, this.activeParticleCount - 5);
                } else if (this.avgFrameTime < 17.0 && this.activeParticleCount < this.targetParticleCount) {
                    this.activeParticleCount = Math.min(this.targetParticleCount, this.activeParticleCount + 2);
                }
            }

            const dpr = window.devicePixelRatio || 1;
            const w = this.canvas.width / dpr;
            const h = this.canvas.height / dpr;
            this.ctx.clearRect(0, 0, w, h);

            // Unit vector in wind flow direction
            // Compass 0° is North (blowing South: dx=0, dy=1), 270° is West (blowing East: dx=1, dy=0)
            const windRad = (this.windAngle * Math.PI) / 180.0;
            const wx = -Math.sin(windRad);
            const wy = Math.cos(windRad);

            // Render Layers
            if (this.isSplitWipe) {
                this.renderSplitWipeMode(w, h, wx, wy);
            } else {
                this.renderStandardMode(w, h, wx, wy);
            }

            this.animFrameId = requestAnimationFrame(this.render);
        }

        renderStandardMode(w, h, wx, wy) {
            // 1. Wake Cones
            if (this.showWakes && this.activeLayout.length > 0) {
                this.drawWakeConesForLayout(this.activeLayout, wx, wy);
            }

            // 2. Wind Particles
            if (this.showParticles) {
                this.drawParticles(w, h, wx, wy, this.activeLayout);
            }

            // 3. Rotating 3-Blade Rotors
            if (this.showRotors && this.activeLayout.length > 0) {
                this.drawRotorsForLayout(this.activeLayout);
            }
        }

        renderSplitWipeMode(w, h, wx, wy) {
            const splitX = this.splitX;

            // --- LEFT REGION: BASELINE LAYOUT ---
            this.ctx.save();
            this.ctx.beginPath();
            this.ctx.rect(0, 0, splitX, h);
            this.ctx.clip();

            if (this.showWakes && this.baselineLayout.length > 0) {
                this.drawWakeConesForLayout(this.baselineLayout, wx, wy);
            }
            if (this.showParticles) {
                this.drawParticles(w, h, wx, wy, this.baselineLayout);
            }
            if (this.showRotors && this.baselineLayout.length > 0) {
                this.drawRotorsForLayout(this.baselineLayout);
            }
            this.ctx.restore();

            // --- RIGHT REGION: QAOA QUANTUM OPTIMAL LAYOUT ---
            this.ctx.save();
            this.ctx.beginPath();
            this.ctx.rect(splitX, 0, w - splitX, h);
            this.ctx.clip();

            if (this.showWakes && this.qaoaLayout.length > 0) {
                this.drawWakeConesForLayout(this.qaoaLayout, wx, wy);
            }
            if (this.showParticles) {
                this.drawParticles(w, h, wx, wy, this.qaoaLayout);
            }
            if (this.showRotors && this.qaoaLayout.length > 0) {
                this.drawRotorsForLayout(this.qaoaLayout);
            }
            this.ctx.restore();

            // --- DRAW SLEEK VERTICAL SPLIT DIVIDER LINE ---
            this.drawSplitDivider(splitX, h);
        }

        drawSplitDivider(x, h) {
            this.ctx.save();
            // Ambient glow
            this.ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
            this.ctx.lineWidth = 4;
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, h);
            this.ctx.stroke();

            // Sharp core line
            this.ctx.strokeStyle = '#ffffff';
            this.ctx.lineWidth = 1.5;
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, h);
            this.ctx.stroke();

            // Center Wipe Handle Badge
            const badgeY = h / 2;
            this.ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
            this.ctx.strokeStyle = '#38bdf8';
            this.ctx.lineWidth = 1.5;
            this.ctx.beginPath();
            this.ctx.roundRect(x - 42, badgeY - 14, 84, 28, 14);
            this.ctx.fill();
            this.ctx.stroke();

            this.ctx.fillStyle = '#ffffff';
            this.ctx.font = '600 11px Inter, sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText('◀ WIPE ▶', x, badgeY);

            this.ctx.restore();
        }

        drawWakeConesForLayout(layout, wx, wy) {
            if (!this.map || layout.length === 0) return;
            this.ctx.save();
            this.ctx.globalCompositeOperation = 'screen'; // Additive blending for overlapping wakes

            // Normal perpendicular to wind
            const nx = -wy;
            const ny = wx;

            layout.forEach((t) => {
                const pt = this.map.latLngToContainerPoint([t.lat, t.lon]);
                
                // Calculate physical pixel length based on map zoom scale
                // Jensen wake cone extends downwind with half-angle k=0.075
                const coneLength = 340; // Pixels downwind
                const startRadius = 14; // Blade hub/tip radius
                const endRadius = startRadius + coneLength * 0.075 * 2.2; // Jensen expansion k=0.075

                const p0_left = { x: pt.x - nx * startRadius, y: pt.y - ny * startRadius };
                const p0_right = { x: pt.x + nx * startRadius, y: pt.y + ny * startRadius };
                const p1_right = { x: pt.x + wx * coneLength + nx * endRadius, y: pt.y + wy * coneLength + ny * endRadius };
                const p1_left = { x: pt.x + wx * coneLength - nx * endRadius, y: pt.y + wy * coneLength - ny * endRadius };

                // Downwind gradient: High deficit red/amber -> dissipating cyan
                const effSpeed = typeof t.effective_mps === 'number' ? t.effective_mps : this.windSpeed;
                const deficit = Math.max(0.0, 1.0 - (effSpeed / this.windSpeed));
                const isHeavyWake = deficit > 0.12;

                const grad = this.ctx.createLinearGradient(pt.x, pt.y, pt.x + wx * coneLength, pt.y + wy * coneLength);
                if (isHeavyWake) {
                    grad.addColorStop(0, 'rgba(239, 68, 68, 0.52)');   // Deep red near rotor
                    grad.addColorStop(0.35, 'rgba(245, 158, 11, 0.38)'); // Amber mid-wake
                    grad.addColorStop(0.75, 'rgba(56, 189, 248, 0.14)'); // Dissipating wake
                    grad.addColorStop(1, 'rgba(56, 189, 248, 0.0)');
                } else {
                    grad.addColorStop(0, 'rgba(245, 158, 11, 0.38)');
                    grad.addColorStop(0.4, 'rgba(56, 189, 248, 0.22)');
                    grad.addColorStop(0.85, 'rgba(56, 189, 248, 0.08)');
                    grad.addColorStop(1, 'rgba(56, 189, 248, 0.0)');
                }

                this.ctx.fillStyle = grad;
                this.ctx.beginPath();
                this.ctx.moveTo(p0_left.x, p0_left.y);
                this.ctx.lineTo(p0_right.x, p0_right.y);
                this.ctx.lineTo(p1_right.x, p1_right.y);
                this.ctx.lineTo(p1_left.x, p1_left.y);
                this.ctx.closePath();
                this.ctx.fill();
            });

            this.ctx.restore();
        }

        drawParticles(w, h, wx, wy, layout) {
            this.ctx.save();
            const count = Math.min(this.activeParticleCount, this.particles.length);
            const turbinePoints = layout.map(t => {
                const pt = this.map.latLngToContainerPoint([t.lat, t.lon]);
                return {
                    x: pt.x,
                    y: pt.y,
                    effSpeed: typeof t.effective_mps === 'number' ? t.effective_mps : this.windSpeed
                };
            });

            for (let i = 0; i < count; i++) {
                const p = this.particles[i];

                // Check wake cone intersection
                let inWake = false;
                let localDeficit = 0.0;
                let nearGap = false;

                for (let k = 0; k < turbinePoints.length; k++) {
                    const tp = turbinePoints[k];
                    const dx = p.x - tp.x;
                    const dy = p.y - tp.y;
                    const downwindDist = dx * wx + dy * wy;

                    if (downwindDist > 0 && downwindDist < 340) {
                        const lateralDist = Math.abs(dx * (-wy) + dy * wx);
                        const wakeRadius = 14 + downwindDist * 0.075 * 2.2;
                        if (lateralDist <= wakeRadius) {
                            inWake = true;
                            localDeficit = Math.max(localDeficit, (1.0 - (downwindDist / 340)) * 0.7);
                            break;
                        }
                    } else if (downwindDist > -40 && downwindDist <= 0) {
                        const lateralDist = Math.abs(dx * (-wy) + dy * wx);
                        if (lateralDist > 16 && lateralDist < 50) {
                            nearGap = true; // Slight acceleration through turbine gaps
                        }
                    }
                }

                p.inWake = inWake;
                p.deficit = localDeficit;

                // Speed adjustment: Decelerate inside wake, accelerate in gaps
                let curSpeed = p.speed;
                if (inWake) {
                    curSpeed *= (1.0 - localDeficit * 0.45); // Decelerate in wake
                    // Add slight turbulent lateral jitter inside wake
                    p.lateralOffset += (Math.random() - 0.5) * 0.4;
                } else if (nearGap) {
                    curSpeed *= 1.15; // Gap acceleration
                }

                // Advance position along wind flow
                p.x += (wx * curSpeed) + (-wy * p.lateralOffset);
                p.y += (wy * curSpeed) + (wx * p.lateralOffset);
                p.age += 1.0;

                // Check out-of-bounds or age expiration -> Respawn Upwind
                const isOutOfBounds = (p.x < -80 || p.x > w + 80 || p.y < -80 || p.y > h + 80);
                if (isOutOfBounds || p.age >= p.maxAge) {
                    this.respawnParticleUpwind(p, w, h, wx, wy);
                    continue;
                }

                // Draw streak with fading tail
                const streakLen = p.length * (curSpeed / p.speed);
                const tailX = p.x - wx * streakLen;
                const tailY = p.y - wy * streakLen;

                // Streak Color: Cyan in clean air -> Amber/Red inside wake
                if (inWake) {
                    if (localDeficit > 0.35) {
                        this.ctx.strokeStyle = `rgba(239, 68, 68, ${p.alpha * 0.9})`; // Red heavy deficit
                        this.ctx.lineWidth = 1.9;
                    } else {
                        this.ctx.strokeStyle = `rgba(245, 158, 11, ${p.alpha * 0.85})`; // Amber moderate deficit
                        this.ctx.lineWidth = 1.6;
                    }
                } else {
                    this.ctx.strokeStyle = `rgba(34, 211, 238, ${p.alpha * 0.75})`; // Cyan clean air
                    this.ctx.lineWidth = 1.2;
                }

                this.ctx.beginPath();
                this.ctx.moveTo(p.x, p.y);
                this.ctx.lineTo(tailX, tailY);
                this.ctx.stroke();
            }

            this.ctx.restore();
        }

        drawRotorsForLayout(layout) {
            this.ctx.save();
            const bladeLen = 22;   // Pixels length
            const bladeWidth = 2.4; // Pixels root width

            layout.forEach((t) => {
                const pt = this.map.latLngToContainerPoint([t.lat, t.lon]);
                const rotor = this.rotorStates.get(t.id);
                if (!rotor) return;

                // Advance rotor angle
                rotor.angle += rotor.speed;

                // 3 white blades at 120° offsets
                for (let b = 0; b < 3; b++) {
                    const angle = rotor.angle + (b * Math.PI * 2 / 3);
                    const tipX = pt.x + Math.cos(angle) * bladeLen;
                    const tipY = pt.y + Math.sin(angle) * bladeLen;

                    // Blade aerodynamic line
                    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.92)';
                    this.ctx.lineWidth = bladeWidth;
                    this.ctx.lineCap = 'round';
                    this.ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';
                    this.ctx.shadowBlur = 4;

                    this.ctx.beginPath();
                    this.ctx.moveTo(pt.x, pt.y);
                    this.ctx.lineTo(tipX, tipY);
                    this.ctx.stroke();

                    // Aerodynamic winglet tip (subtle red warning marker)
                    this.ctx.fillStyle = '#ef4444';
                    this.ctx.beginPath();
                    this.ctx.arc(tipX, tipY, 1.4, 0, Math.PI * 2);
                    this.ctx.fill();
                }

                // Central spinner hub
                this.ctx.fillStyle = '#ffffff';
                this.ctx.shadowBlur = 2;
                this.ctx.shadowColor = 'rgba(0,0,0,0.5)';
                this.ctx.beginPath();
                this.ctx.arc(pt.x, pt.y, 3.2, 0, Math.PI * 2);
                this.ctx.fill();
            });

            this.ctx.restore();
        }
    }

    // Export to window
    window.WindSimulationEngine = WindSimulationEngine;

})(window);
