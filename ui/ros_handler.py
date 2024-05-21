import rospy

from drive_msgs.msg import *
from std_msgs.msg import Float32MultiArray

STEER_RATIO = 12.9
MPS_TO_KPH = 3.6

class ROSHandler():
    def __init__(self):
        rospy.init_node('ui', anonymous=False)
        
        self.set_values()
        self.set_publisher_protocol()
        self.set_subscriber_protocol()

    def set_values(self):
        self.ego_value = {'velocity':0, 'steer': 0, 'accel': 0, 'brake': 0, 'gear':'P'}
        self.target_value = {'velocity':0, 'steer': 0, 'accel': 0, 'brake': 0}
        self.system_status = {'mode': 0, 'signal':0}
        self.user_input = Float32MultiArray()
        self.user_input.data = [0,0]

    def set_publisher_protocol(self):
        self.pub_user_input = rospy.Publisher('/ui/user_input',Float32MultiArray, queue_size=1)
        
    def set_subscriber_protocol(self):
        rospy.Subscriber('/CANOutput', CANOutput, self.can_output_cb)
        rospy.Subscriber('/VehicleState', VehicleState, self.vehicle_state_cb)
        rospy.Subscriber('/control/target_actuator', Actuator, self.target_actuator_cb)
        rospy.Subscriber('/NavigationData', NavigationData, self.navigation_data_cb)
        rospy.Subscriber('/SystemStatus', SystemStatus, self.system_status_cb)

    def can_output_cb(self, msg):
        self.ego_value['steer'] = float(msg.StrAng.data)
        self.ego_value['accel'] = float(msg.Long_ACCEL.data)
        self.ego_value['brake'] = float(msg.BRK_CYLINDER.data)
    
    def vehicle_state_cb(self, msg):
        self.ego_value['velocity'] = int(msg.velocity.data*MPS_TO_KPH)
        self.ego_value['gear'] = str(msg.gear.data)

    def target_actuator_cb(self, msg):
        self.target_value['steer'] = msg.steer.data
        self.target_value['accel'] = msg.accel.data
        self.target_value['brake'] = msg.brake.data
    
    def navigation_data_cb(self, msg):
        self.target_value['velocity'] = int(msg.plannedVelocity.data*MPS_TO_KPH)
    
    def system_status_cb(self, msg):
        self.system_status['mode'] = int(msg.systemMode.data)
        self.system_status['signal'] = int(msg.systemSignal.data)
    
    def publish(self):
        self.pub_user_input.publish(self.user_input)