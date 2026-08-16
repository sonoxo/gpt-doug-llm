// ✓ 9/10 Mobile App — React Native wrapper for all 10 agents
// Deploy free: Expo (expo.dev) — free builds and hosting
// Run: npm install && npx expo start

import React, { useState } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, Alert } from 'react-native';

const AGENTS = [
  { id: 1, icon: '🔒', name: 'Sentinel Bot', track: 'Everyday', desc: 'Home network security scanner' },
  { id: 2, icon: '📄', name: 'Document Drafter', track: 'Professional', desc: 'Contract review & risk flagging' },
  { id: 3, icon: '🥫', name: 'NeighborHelp', track: 'Good Neighbor', desc: 'Food bank inventory coordinator' },
  { id: 4, icon: '📅', name: 'Meeting Sentinel', track: 'Everyday', desc: 'Calendar conflict resolver' },
  { id: 5, icon: '💊', name: 'Health Tracker', track: 'Everyday', desc: 'Medication & appointment manager' },
  { id: 6, icon: '💰', name: 'Invoice Ninja', track: 'Professional', desc: 'Freelancer invoice & payment chaser' },
  { id: 7, icon: '🚨', name: 'Emergency Mesh', track: 'Good Neighbor', desc: 'Neighborhood emergency coordinator' },
  { id: 8, icon: '🔍', name: 'Code Reviewer ★', track: 'Professional', desc: 'Autonomous PR review & security gate' },
  { id: 9, icon: '💳', name: 'Expense Sentinel', track: 'Everyday', desc: 'Receipt scanner & budget tracker' },
  { id: 10, icon: '🏫', name: 'School Coordinator', track: 'Good Neighbor', desc: 'PTA volunteer matcher' },
];

const TRACK_COLORS: Record<string, string> = {
  'Everyday': '#00ff88', 'Professional': '#ffd700', 'Good Neighbor': '#00ccff'
};

export default function App() {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>🛰️ GPT DOUG</Text>
      <Text style={styles.subtitle}>10 Agents for Humans</Text>
      <ScrollView style={styles.list}>
        {AGENTS.map((agent) => (
          <TouchableOpacity
            key={agent.id}
            style={[styles.card, { borderLeftColor: TRACK_COLORS[agent.track] }]}
            onPress={() => {
              setSelected(agent.id);
              Alert.alert(`${agent.icon} ${agent.name}`, agent.desc + '\n\nTrack: ' + agent.track);
            }}
          >
            <Text style={styles.cardIcon}>{agent.icon}</Text>
            <View style={styles.cardText}>
              <Text style={styles.cardName}>{agent.name}</Text>
              <Text style={styles.cardDesc}>{agent.desc}</Text>
              <Text style={[styles.cardTrack, { color: TRACK_COLORS[agent.track] }]}>{agent.track}</Text>
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <Text style={styles.footer}>github.com/sonoxo/gpt-doug-llm · MIT</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a1a', paddingTop: 60 },
  title: { fontSize: 28, color: '#00ff88', textAlign: 'center', fontWeight: 'bold' },
  subtitle: { fontSize: 14, color: '#888', textAlign: 'center', marginBottom: 20 },
  list: { flex: 1, paddingHorizontal: 16 },
  card: { flexDirection: 'row', backgroundColor: 'rgba(255,255,255,0.05)', padding: 16, marginVertical: 4, borderRadius: 12, borderLeftWidth: 3 },
  cardIcon: { fontSize: 32, marginRight: 12 },
  cardText: { flex: 1 },
  cardName: { fontSize: 16, color: '#e0e0e0', fontWeight: 'bold' },
  cardDesc: { fontSize: 12, color: '#888', marginTop: 4 },
  cardTrack: { fontSize: 10, marginTop: 4, fontWeight: 'bold' },
  footer: { fontSize: 10, color: '#444', textAlign: 'center', padding: 20 },
});
