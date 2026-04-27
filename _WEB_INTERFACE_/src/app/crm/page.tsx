import React from 'react';
import { prisma } from '@/lib/prisma';
import { Mail, User, MessageSquare, Calendar, ShieldAlert, Globe, Monitor as MonitorIcon, Eye } from 'lucide-react';

export const dynamic = 'force-dynamic';

export default async function CrmPage() {
  const messages = await prisma.message.findMany({
    orderBy: {
      createdAt: 'desc',
    },
  });

  const visitors = await prisma.visitor.findMany({
    orderBy: {
      createdAt: 'desc',
    },
    take: 50, // Ultimi 50 visitatori
  });

  return (
    <div className="min-h-screen bg-[#f0f2f5] p-8 md:p-20 font-sans">
      <div className="max-w-6xl mx-auto">
        <header className="mb-16 flex flex-col md:flex-row md:items-end justify-between gap-8">
          <div>
            <div className="flex items-center gap-3 text-brand font-bold uppercase tracking-[0.3em] text-[10px] mb-4">
              <ShieldAlert size={14} />
              Area Riservata
            </div>
            <h1 className="text-5xl md:text-7xl font-display font-extrabold tracking-tighter">
              CRM <span className="text-brand italic font-serif">Dashboard.</span>
            </h1>
          </div>
          <div className="flex gap-4">
            <div className="bg-white px-6 py-3 rounded-2xl shadow-sm border border-dark/5">
              <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30">Messaggi</p>
              <p className="text-3xl font-display font-black text-brand">{messages.length}</p>
            </div>
            <div className="bg-white px-6 py-3 rounded-2xl shadow-sm border border-dark/5">
              <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30">Visitatori</p>
              <p className="text-3xl font-display font-black text-accent">{visitors.length}</p>
            </div>
          </div>
        </header>

        <div className="space-y-20">
          {/* Sezione Messaggi */}
          <section>
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <MessageSquare className="text-brand" /> Messaggi Ricevuti
            </h2>
            <div className="grid gap-6">
              {messages.length === 0 ? (
                <div className="bg-white/50 backdrop-blur-md rounded-[2rem] p-20 text-center border border-white">
                  <MessageSquare className="w-16 h-16 mx-auto mb-6 opacity-10" />
                  <p className="text-xl font-bold opacity-30 tracking-tight uppercase">Nessun messaggio ricevuto</p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div 
                    key={msg.id} 
                    className="bg-white/70 backdrop-blur-xl rounded-[2.5rem] p-8 md:p-12 border border-white shadow-xl hover:shadow-2xl transition-all duration-500 group"
                  >
                    <div className="grid md:grid-cols-12 gap-8 items-start">
                      <div className="md:col-span-4 space-y-6">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-2xl bg-brand/10 text-brand flex items-center justify-center">
                            <User size={20} />
                          </div>
                          <div>
                            <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30">Mittente</p>
                            <p className="font-bold text-lg">{msg.name}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-2xl bg-accent/10 text-accent flex items-center justify-center">
                            <Mail size={20} />
                          </div>
                          <div>
                            <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30">Email</p>
                            <p className="font-bold">{msg.email}</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-2xl bg-dark/5 text-dark flex items-center justify-center">
                            <Globe size={20} />
                          </div>
                          <div>
                            <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30">Indirizzo IP</p>
                            <p className="font-mono font-bold text-brand">{msg.ip || "Sconosciuto"}</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-2xl bg-dark/5 text-dark flex items-center justify-center">
                            <Calendar size={20} />
                          </div>
                          <div>
                            <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30">Data Invio</p>
                            <p className="font-bold text-sm">
                              {new Date(msg.createdAt).toLocaleDateString('it-IT', {
                                day: '2-digit',
                                month: 'long',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="md:col-span-8 bg-white/50 rounded-[2rem] p-8 border border-white/50 relative">
                        <div className="absolute top-6 right-8 opacity-[0.05]">
                          <MessageSquare size={60} />
                        </div>
                        <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30 mb-4">Dettagli Progetto</p>
                        <p className="text-lg leading-relaxed text-dark/80 whitespace-pre-wrap">
                          {msg.project}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          {/* Sezione Visitatori */}
          <section>
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Eye className="text-accent" /> Log Visitatori (Real-time)
            </h2>
            <div className="bg-white/70 backdrop-blur-xl rounded-[2.5rem] border border-white shadow-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-dark/5">
                      <th className="p-6 text-[10px] font-extrabold uppercase tracking-widest opacity-50">IP Address</th>
                      <th className="p-6 text-[10px] font-extrabold uppercase tracking-widest opacity-50">Browser / User Agent</th>
                      <th className="p-6 text-[10px] font-extrabold uppercase tracking-widest opacity-50">Data e Ora</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark/5">
                    {visitors.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="p-10 text-center opacity-30 font-bold uppercase tracking-tight">Nessun visitatore tracciato</td>
                      </tr>
                    ) : (
                      visitors.map((v) => (
                        <tr key={v.id} className="hover:bg-brand/5 transition-colors group">
                          <td className="p-6">
                            <span className="font-mono font-bold text-brand bg-brand/10 px-3 py-1 rounded-lg">{v.ip}</span>
                          </td>
                          <td className="p-6 text-sm text-dark/60 truncate max-w-xs" title={v.userAgent || ""}>
                            {v.userAgent || "N/A"}
                          </td>
                          <td className="p-6 text-sm font-medium">
                            {new Date(v.createdAt).toLocaleString('it-IT', {
                              day: '2-digit',
                              month: '2-digit',
                              year: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit'
                            })}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </div>

        <footer className="mt-20 text-center opacity-20 hover:opacity-100 transition-opacity duration-500">
          <p className="text-[10px] font-bold uppercase tracking-[0.5em]">Creative Engineering Studio - Database Locale</p>
        </footer>
      </div>
    </div>
  );
}
