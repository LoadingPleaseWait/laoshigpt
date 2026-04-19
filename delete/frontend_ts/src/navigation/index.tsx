import React from 'react';
import { View, Text } from 'react-native';

export function AppNavigator() {
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <Text style={{ fontSize: 24, fontWeight: '700', marginBottom: 8 }}>LaoshiGPT</Text>
      <Text style={{ textAlign: 'center' }}>
        Scaffold ready: next step is wiring Onboarding → ModeSelect → Practice → Summary → Review navigation.
      </Text>
    </View>
  );
}
