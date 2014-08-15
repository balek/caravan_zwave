#!/usr/bin/env python

import libopenzwave  # @UnresolvedImport

from twisted.internet import reactor

from caravan.base import VanSession, VanModule, VanDevice, deviceCommand, Int, List, Decimal, Str, Bool



class ZWaveValue(VanDevice):
    list = None
    def __init__(self, parent, valueId):
        self.id = valueId['id']
        self['label'] = valueId['label']
        self.state = valueId['value']
        #self.units = valueId['units']
        self.setStateType(valueId)
        if valueId['readOnly']:
            self.set = None
        if manager.isValueWriteOnly(self.id):
            self.get = None
        super(ZWaveValue, self).__init__(parent, 'value%i' % valueId['index'])

    def setStateType(self, valueId):
        valueType = valueId['type']
        if valueType == 'Bool':
            self.stateType = Bool()
        if valueType in ('Byte', 'Short', 'Int'):
            self.stateType = Int(min=manager.getValueMin(self.id), max=manager.getValueMax(self.id))
        elif valueType == 'List':
            self.stateType = List(*manager.getValueListItems(self.id))
        elif valueType == 'Decimal':
            self.stateType = Decimal(precision=manager.getValueFloatPrecision(self.id))
        else:
            self.stateType = Str()

    @deviceCommand()
    def get(self):
        return manager.getValue(self.id)

    def set(self, value):
        return manager.setValue(self.id, value)


class ZWaveCommandClassInstance(VanDevice):
    pass


class ZWaveNode(VanDevice):
    def __init__(self, parent, nodeId):
        self.nodeId = nodeId
        super(ZWaveNode, self).__init__(parent, 'node%i' % nodeId)

    def getCommandClassInstance(self, valueId):
        commandClass = valueId['commandClass']
        instanceIdx = valueId['instance']
        name = commandClass[len('COMMAND_CLASS_'):]
        name = ''.join([ n.title() for n in name.lower().split('_') ])
        name = name[0].lower() + name[1:]
        if instanceIdx > 1:
            name += str(instanceIdx)
        instance = self.children.get(name)
        if not instance:
            instance = ZWaveCommandClassInstance(self, name)
        return instance

    @deviceCommand(Int(0, 255))
    def setLevel(self, value):
        manager.setNodeLevel(self.parent.homeId, self.nodeId, value)

    @deviceCommand(Int(), Int())
    def setConfigParam(self, param, value):
        manager.setConfigParam(self.parent.homeId, self.nodeId, param, value)

    def handleNotification(self, notificationType, **notification):
        if hasattr(self, 'on' + notificationType):
            getattr(self, 'on' + notificationType)(**notification)
        else:
            return 'No handler for node notification:', notification

    def onNodeProtocolInfo(self, **notification):
        """Basic node information has been receievd, such as whether
        the node is a listening device, a routing device and its baud
        rate and basic, generic and specific types. It is after this
        notification that you can call Manager::GetNodeType to obtain
        a label containing the device description. """
        pass

    def onValueAdded(self, valueId, **notification):
        """A new node value has been added to OpenZWave's list.
        These notifications occur after a node has been discovered,
        and details of its command classes have been received. Each
        command class may generate one or more values depending on
        the complexity of the item being represented."""

        instance = self.getCommandClassInstance(valueId)
        ZWaveValue(instance, valueId)

    def onValueRemoved(self, valueId, **notification):
        """A node value has been removed from OpenZWave's list.
        This only occurs when a node is removed."""

        name = 'value%i' % valueId['index']
        instance = self.getCommandClassInstance(valueId)
        del instance.children[name]
        if not instance.children:
            del self.children[instance.name]

    def onValueChanged(self, valueId, **notification):
        """A node value has been updated from the Z-Wave network
        and it is different from the previous value."""

        name = 'value%i' % valueId['index']
        instance = self.getCommandClassInstance(valueId)
        instance.children[name].changeState(valueId['value'])

    def onGroup(self, **notification):
        """The associations for the node have changed. The application
        should rebuild any group information it holds about the node."""
        pass

    def onNodeNaming(self, **notification):
        """One of the node names has changed (name, manufacturer, product)."""
        pass

    def onNotification(self, notificationCode, **notification):
        """An error has occured that we need to report."""

        code = libopenzwave.PyNotificationCodes[notificationCode]

    def onEssentialNodeQueriesComplete(self, **notification):
        """The queries on a node that are essential to its operation
        have been completed. The node can now handle incoming messages."""
        pass


class ZWaveNetwork(VanDevice):
    def __init__(self, parent, homeId):
        self.homeId = homeId
        super(ZWaveNetwork, self).__init__(parent, 'network%i' % homeId)

    def handleNotification(self, notificationType, nodeId, **notification):
        if hasattr(self, 'on' + notificationType):
            getattr(self, 'on' + notificationType)(nodeId=nodeId, **notification)
        elif nodeId and nodeId != 255:
            node = self.children['node%i' % nodeId]
            node.handleNotification(notificationType=notificationType, **notification)
        else:
            print 'No handler for notification:', nodeId, notification

    def onNodeNew(self, nodeId, **notification):
        """A new node has been found (not already stored in zwcfg*.xml file)"""
        pass

    def onNodeAdded(self, nodeId, **notification):
        """A new node has been added to OpenZWave's list. This may be
        due to a device being added to the Z-Wave network, or because
        the application is initializing itself."""

        ZWaveNode(self, nodeId)

    def onNodeRemoved(self, nodeId, **notification):
        """A node has been removed from OpenZWave's list. This may be
        due to a device being removed from the Z-Wave network, or
        because the application is closing."""

        del self.children['node%i' % nodeId]

    def onAwakeNodesQueried(self, **notification):
        """All awake nodes have been queried, so client application
        can expected complete data for these nodes."""
        pass

    def onAllNodesQueriedSomeDead(self, **notification):
        """All nodes have been queried but some dead nodes found."""
        pass

    def onAllNodesQueried(self, **notification):
        """All nodes have been queried, so client application can expected complete data."""
        pass


class ZWaveManager(VanModule, libopenzwave.PyManager):
    def __init__(self, session):
        libopenzwave.PyManager(self)
        super(ZWaveManager, self).__init__(session, 'zwave')

    def emitEvent(self, event, *args, **kwargs):
        reactor.callFromThread(super(ZWaveManager, self).emitEvent, event, *args, **kwargs)  # @UndefinedVariable

    def registerCommand(self, *args, **kwargs):
        reactor.callFromThread(super(ZWaveManager, self).registerCommand, *args, **kwargs)  # @UndefinedVariable

    def setValue(self, *args, **kwargs):
        reactor.callInThread(libopenzwave.PyManager.setValue, self, *args, **kwargs)  # @UndefinedVariable
        
    def handleNotification(self, notificationType, homeId, **notification):
        if hasattr(self, 'on' + notificationType):
            getattr(self, 'on' + notificationType)(homeId=homeId, **notification)
        elif homeId:
            network = self.children['network%i' % homeId]
            network.handleNotification(notificationType=notificationType, **notification)
        else:
            print 'No handler for notification:', homeId, notification
            
    def onDriverReady(self, homeId, **notification):
        ZWaveNetwork(self, homeId)


class AppSession(VanSession):
    def start(self):
        global manager
        manager = self

        options = libopenzwave.PyOptions()
        options.create('/etc/openzwave/', '/root/zwave/', '')
#        options.addOptionBool('ConsoleOutput', False)
        options.addOptionBool('Logging', False)
#        options.addOptionBool('SaveConfiguration', True)
        options.lock()

        manager = ZWaveManager(self)
        manager.create()
        manager.addWatcher(handleNotification)
        manager.addDriver('/dev/usbzwave')

    def onLeave(self, details):
        for network in manager.children.values():
            manager.writeConfig(network.homeId)


def handleNotification(notification):
    manager.handleNotification(**notification)


if __name__ == '__main__':
    from autobahn.twisted.wamp import ApplicationRunner
    runner = ApplicationRunner("ws://127.0.0.1:8080/ws", "realm1")
    runner.run(AppSession)
