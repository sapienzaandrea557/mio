import React from "react";

const ServiceCard = ({ icon, title, description, tags, color }: any) => {
  const colorClasses: { [key: string]: string } = {
    brand: "bg-brand/10",
    accent: "bg-accent/10",
    dark: "bg-dark/10",
  };

  return (
    <div className="glass-card p-10 reveal-up group hover:border-brand/50 transition-all duration-500">
      <div className={`w-16 h-16 ${colorClasses[color] || "bg-brand/10"} rounded-2xl flex items-center justify-center mb-8 group-hover:scale-110 group-hover:rotate-3 transition-transform duration-500`}>
        {icon}
      </div>
      <h3 className="text-2xl font-extrabold mb-4 uppercase tracking-tighter group-hover:text-brand transition-colors">{title}</h3>
      <p className="text-dark/50 leading-relaxed mb-6">{description}</p>
      <ul className="space-y-2 text-sm font-bold opacity-30 group-hover:opacity-60 transition-opacity uppercase tracking-widest">
        {tags.map((tag: string) => (
          <li key={tag} className="hover:text-brand transition-colors cursor-default">
            • {tag}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ServiceCard;
