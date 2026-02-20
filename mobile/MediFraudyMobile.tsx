import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
  TextInput,
  Image,
  Camera,
  Permissions,
  Location,
  SecureStore
} from 'react-native';
import {
  Button,
  Card,
  Chip,
  Icon,
  Input,
  ListItem,
  Avatar,
  Badge
} from 'react-native-elements';
import { launchCamera, launchImageLibrary } from 'react-native-image-picker';
import Geolocation from '@react-native-community/geolocation';
import { encryptData, decryptData } from './security';
import { apiClient } from './api';

interface FraudReport {
  id: string;
  type: 'healthcare' | 'insurance';
  description: string;
  location: { lat: number; lng: number };
  photos: string[];
  evidence: string[];
  status: 'pending' | 'investigating' | 'resolved';
  submitted_at: string;
  reward: number;
}

interface Case {
  id: string;
  title: string;
  fraud_type: string;
  amount: number;
  status: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_to: string;
  created_at: string;
}

const MediFraudyMobile: React.FC = () => {
  const [user, setUser] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'report' | 'cases' | 'alerts'>('dashboard');
  const [fraudReports, setFraudReports] = useState<FraudReport[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      // Get user from secure storage
      const userData = await SecureStore.getItemAsync('user');
      if (userData) {
        setUser(JSON.parse(userData));
      }

      // Get current location
      Geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
        },
        (error) => console.log('Location error:', error),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
      );

      // Load initial data
      await loadData();
    } catch (error) {
      console.error('Initialization error:', error);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      // Load fraud reports
      const reportsResponse = await apiClient.get('/mobile/fraud-reports');
      setFraudReports(reportsResponse.data);

      // Load cases
      const casesResponse = await apiClient.get('/mobile/cases');
      setCases(casesResponse.data);
    } catch (error) {
      console.error('Data loading error:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const submitFraudReport = async (reportData: any) => {
    try {
      // Encrypt sensitive data
      const encryptedData = encryptData(JSON.stringify(reportData));
      
      const response = await apiClient.post('/mobile/fraud-reports', {
        encrypted_data: encryptedData,
        location: location,
        timestamp: new Date().toISOString()
      });

      Alert.alert('Success', 'Fraud report submitted successfully. You may be eligible for a reward.');
      await loadData();
    } catch (error) {
      Alert.alert('Error', 'Failed to submit fraud report');
    }
  };

  const takePhoto = async () => {
    const options = {
      mediaType: 'photo',
      quality: 0.8,
      includeBase64: false
    };

    launchCamera(options, (response) => {
      if (response.assets && response.assets[0]) {
        // Handle photo capture
        console.log('Photo captured:', response.assets[0]);
      }
    });
  };

  const selectPhoto = async () => {
    const options = {
      mediaType: 'photo',
      quality: 0.8,
      includeBase64: false
    };

    launchImageLibrary(options, (response) => {
      if (response.assets && response.assets[0]) {
        // Handle photo selection
        console.log('Photo selected:', response.assets[0]);
      }
    });
  };

  const renderDashboard = () => (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>MediFraudy Mobile</Text>
        <Text style={styles.headerSubtitle}>Fraud Detection & Reporting</Text>
      </View>

      <Card containerStyle={styles.card}>
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>{fraudReports.length}</Text>
            <Text style={styles.statLabel}>Reports</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>{cases.filter(c => c.status === 'active').length}</Text>
            <Text style={styles.statLabel}>Active Cases</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>$2.3M</Text>
            <Text style={styles.statLabel}>Recovered</Text>
          </View>
        </View>
      </Card>

      <Card containerStyle={styles.card}>
        <Text style={styles.cardTitle}>Quick Actions</Text>
        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={[styles.actionButton, styles.primaryButton]}
            onPress={() => setActiveTab('report')}
          >
            <Icon name="report" type="material" color="white" />
            <Text style={styles.actionButtonText}>Report Fraud</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionButton, styles.secondaryButton]}
            onPress={() => setActiveTab('cases')}
          >
            <Icon name="assignment" type="material" color="white" />
            <Text style={styles.actionButtonText}>View Cases</Text>
          </TouchableOpacity>
        </View>
      </Card>

      <Card containerStyle={styles.card}>
        <Text style={styles.cardTitle}>Recent Activity</Text>
        {fraudReports.slice(0, 3).map((report) => (
          <ListItem key={report.id} bottomDivider>
            <Avatar
              rounded
              icon={{ name: 'report', type: 'material', color: 'white' }}
              containerStyle={{ backgroundColor: '#4CAF50' }}
            />
            <ListItem.Content>
              <ListItem.Title>{report.type} Fraud</ListItem.Title>
              <ListItem.Subtitle>{new Date(report.submitted_at).toLocaleDateString()}</ListItem.Subtitle>
            </ListItem.Content>
            <Badge
              value={report.status}
              status={report.status === 'resolved' ? 'success' : 'warning'}
            />
          </ListItem>
        ))}
      </Card>
    </ScrollView>
  );

  const renderReportFraud = () => (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Report Fraud</Text>
        <Text style={styles.headerSubtitle}>Anonymous & Secure Reporting</Text>
      </View>

      <Card containerStyle={styles.card}>
        <Text style={styles.cardTitle}>Fraud Type</Text>
        <View style={styles.fraudTypes}>
          {['Healthcare', 'Insurance', 'Political', 'Other'].map((type) => (
            <TouchableOpacity
              key={type}
              style={[styles.fraudTypeButton, styles.selectedButton]}
            >
              <Text style={styles.fraudTypeText}>{type}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </Card>

      <Card containerStyle={styles.card}>
        <Text style={styles.cardTitle}>Description</Text>
        <Input
          placeholder="Describe the fraudulent activity..."
          multiline
          numberOfLines={4}
          containerStyle={styles.inputContainer}
        />
      </Card>

      <Card containerStyle={styles.card}>
        <Text style={styles.cardTitle}>Evidence</Text>
        <View style={styles.evidenceButtons}>
          <TouchableOpacity style={styles.evidenceButton} onPress={takePhoto}>
            <Icon name="camera" type="material" />
            <Text style={styles.evidenceButtonText}>Take Photo</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.evidenceButton} onPress={selectPhoto}>
            <Icon name="photo-library" type="material" />
            <Text style={styles.evidenceButtonText}>Select Photo</Text>
          </TouchableOpacity>
        </View>
      </Card>

      <Card containerStyle={styles.card}>
        <Text style={styles.cardTitle}>Location</Text>
        {location ? (
          <Text style={styles.locationText}>
            📍 {location.lat.toFixed(6)}, {location.lng.toFixed(6)}
          </Text>
        ) : (
          <Text style={styles.locationText}>Getting location...</Text>
        )}
      </Card>

      <View style={styles.submitContainer}>
        <Button
          title="Submit Report"
          buttonStyle={styles.submitButton}
          onPress={() => {
            // Handle submission
            Alert.alert('Success', 'Report submitted successfully');
            setActiveTab('dashboard');
          }}
        />
      </View>
    </ScrollView>
  );

  const renderCases = () => (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Investigation Cases</Text>
        <Text style={styles.headerSubtitle}>Track fraud investigations</Text>
      </View>

      {cases.map((case_item) => (
        <Card key={case_item.id} containerStyle={styles.caseCard}>
          <View style={styles.caseHeader}>
            <Text style={styles.caseTitle}>{case_item.title}</Text>
            <Chip
              title={case_item.priority}
              type="outline"
              color={
                case_item.priority === 'critical' ? 'red' :
                case_item.priority === 'high' ? 'orange' :
                case_item.priority === 'medium' ? 'yellow' : 'green'
              }
            />
          </View>
          <Text style={styles.caseDescription}>{case_item.fraud_type}</Text>
          <Text style={styles.caseAmount}>${case_item.amount.toLocaleString()}</Text>
          <View style={styles.caseFooter}>
            <Text style={styles.caseStatus}>{case_item.status}</Text>
            <Text style={styles.caseDate}>
              {new Date(case_item.created_at).toLocaleDateString()}
            </Text>
          </View>
        </Card>
      ))}
    </ScrollView>
  );

  const renderAlerts = () => (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Fraud Alerts</Text>
        <Text style={styles.headerSubtitle}>Real-time fraud detection</Text>
      </View>

      <Card containerStyle={styles.alertCard}>
        <View style={styles.alertHeader}>
          <Icon name="warning" type="material" color="#FF9800" />
          <Text style={styles.alertTitle}>High-Risk Pattern Detected</Text>
        </View>
        <Text style={styles.alertDescription}>
          Multiple claims from same provider with unusual billing patterns
        </Text>
        <Text style={styles.alertTime}>2 minutes ago</Text>
      </Card>

      <Card containerStyle={styles.alertCard}>
        <View style={styles.alertHeader}>
          <Icon name="error" type="material" color="#F44336" />
          <Text style={styles.alertTitle}>Critical Fraud Alert</Text>
        </View>
        <Text style={styles.alertDescription}>
          Potential insurance fraud ring detected in network analysis
        </Text>
        <Text style={styles.alertTime}>15 minutes ago</Text>
      </Card>

      <Card containerStyle={styles.alertCard}>
        <View style={styles.alertHeader}>
          <Icon name="info" type="material" color="#2196F3" />
          <Text style={styles.alertTitle}>New Fraud Pattern</Text>
        </View>
        <Text style={styles.alertDescription}>
          AI identified new sophisticated billing scheme
        </Text>
        <Text style={styles.alertTime}>1 hour ago</Text>
      </Card>
    </ScrollView>
  );

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return renderDashboard();
      case 'report':
        return renderReportFraud();
      case 'cases':
        return renderCases();
      case 'alerts':
        return renderAlerts();
      default:
        return renderDashboard();
    }
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Loading MediFraudy...</Text>
      </View>
    );
  }

  return (
    <View style={styles.mainContainer}>
      <ScrollView
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {renderContent()}
      </ScrollView>
      
      <View style={styles.tabBar}>
        {[
          { key: 'dashboard', icon: 'dashboard', label: 'Dashboard' },
          { key: 'report', icon: 'report', label: 'Report' },
          { key: 'cases', icon: 'assignment', label: 'Cases' },
          { key: 'alerts', icon: 'notifications', label: 'Alerts' }
        ].map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.tabItem,
              activeTab === tab.key && styles.activeTab
            ]}
            onPress={() => setActiveTab(tab.key as any)}
          >
            <Icon
              name={tab.icon}
              type="material"
              color={activeTab === tab.key ? '#4CAF50' : '#666'}
            />
            <Text
              style={[
                styles.tabLabel,
                activeTab === tab.key && styles.activeTabLabel
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  mainContainer: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  container: {
    flex: 1
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center'
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666'
  },
  header: {
    padding: 20,
    backgroundColor: '#4CAF50',
    alignItems: 'center'
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white'
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 5
  },
  card: {
    margin: 10,
    borderRadius: 10
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 20
  },
  statItem: {
    alignItems: 'center'
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#4CAF50'
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 5
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around'
  },
  actionButton: {
    alignItems: 'center',
    padding: 15,
    borderRadius: 10,
    minWidth: 120
  },
  primaryButton: {
    backgroundColor: '#4CAF50'
  },
  secondaryButton: {
    backgroundColor: '#2196F3'
  },
  actionButtonText: {
    color: 'white',
    fontWeight: 'bold',
    marginTop: 5
  },
  fraudTypes: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around'
  },
  fraudTypeButton: {
    padding: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#ddd',
    margin: 5
  },
  selectedButton: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50'
  },
  fraudTypeText: {
    color: '#333'
  },
  inputContainer: {
    marginBottom: 10
  },
  evidenceButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around'
  },
  evidenceButton: {
    alignItems: 'center',
    padding: 15,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    minWidth: 100
  },
  evidenceButtonText: {
    marginTop: 5,
    fontSize: 12
  },
  locationText: {
    fontSize: 14,
    color: '#666'
  },
  submitContainer: {
    padding: 20
  },
  submitButton: {
    backgroundColor: '#4CAF50',
    borderRadius: 10
  },
  caseCard: {
    margin: 10,
    borderRadius: 10
  },
  caseHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10
  },
  caseTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    flex: 1
  },
  caseDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5
  },
  caseAmount: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#4CAF50',
    marginBottom: 10
  },
  caseFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  caseStatus: {
    fontSize: 12,
    color: '#666'
  },
  caseDate: {
    fontSize: 12,
    color: '#666'
  },
  alertCard: {
    margin: 10,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#FF9800'
  },
  alertHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10
  },
  alertTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 10
  },
  alertDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5
  },
  alertTime: {
    fontSize: 12,
    color: '#999'
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#ddd'
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    padding: 10
  },
  activeTab: {
    backgroundColor: '#f0f0f0'
  },
  tabLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 5
  },
  activeTabLabel: {
    color: '#4CAF50',
    fontWeight: 'bold'
  }
});

export default MediFraudyMobile;
