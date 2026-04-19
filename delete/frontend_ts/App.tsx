import React from 'react';
import { SafeAreaView, StatusBar } from 'react-native';
import { AppNavigator } from './src/navigation';

export default function App() {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <StatusBar barStyle="dark-content" />
      <AppNavigator />
    </SafeAreaView>
  );
}
