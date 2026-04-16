"use client";
import React, { useEffect, useRef } from "react";
import gsap from "gsap";

const DynamicBackground = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Floating abstract shapes/images
      const shapes = document.querySelectorAll(".abstract-shape");
      shapes.forEach((shape, i) => {
        gsap.to(shape, {
          x: "random(-100, 100)",
          y: "random(-100, 100)",
          rotation: "random(-20, 20)",
          duration: "random(10, 20)",
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
          delay: i * 0.5
        });
      });

      const handleMouseMove = (e: MouseEvent) => {
        const { clientX, clientY } = e;
        const xPos = (clientX / window.innerWidth - 0.5);
        const yPos = (clientY / window.innerHeight - 0.5);

        shapes.forEach((shape, i) => {
          const speed = (i + 1) * 20;
          gsap.to(shape, {
            x: `+=${xPos * speed}`,
            y: `+=${yPos * speed}`,
            duration: 2,
            ease: "power2.out"
          });
        });
      };

      window.addEventListener("mousemove", handleMouseMove);
      return () => window.removeEventListener("mousemove", handleMouseMove);
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} className="fixed inset-0 -z-20 overflow-hidden pointer-events-none bg-[#f0f2f5]">
      {/* Soft abstract background images/shapes */}
      <div className="abstract-shape absolute top-[-10%] left-[-5%] w-[600px] h-[600px] bg-indigo-200/30 blur-[120px] rounded-full" />
      <div className="abstract-shape absolute bottom-[-10%] right-[-5%] w-[700px] h-[700px] bg-purple-200/30 blur-[130px] rounded-full" />
      <div className="abstract-shape absolute top-[30%] right-[10%] w-[500px] h-[500px] bg-cyan-200/20 blur-[100px] rounded-full" />
      <div className="abstract-shape absolute bottom-[20%] left-[10%] w-[400px] h-[400px] bg-pink-200/20 blur-[110px] rounded-full" />
      
      {/* Texture overlay */}
      <div className="fixed inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: `url('https://www.transparenttextures.com/patterns/cubes.png')` }} />
    </div>
  );
};

export default DynamicBackground;
