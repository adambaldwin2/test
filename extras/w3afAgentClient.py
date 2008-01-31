from core.controllers.w3afAgent.client.w3afAgentClient import w3afAgentClient
import core.controllers.outputManager as om
import socket
om.out.setOutputPlugins( ['console'] )

w3afAgentClient().start()
