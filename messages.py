from pydbus import SystemBus
bus = SystemBus()

dbus_endpoint = "org.asamk.Signal"


def get_dbus_account_interface():
    signal = bus.get(dbus_endpoint)
    accounts = signal.listAccounts()
    # returns [/org/asamk/Signal/_49number] or empty list
    if len(accounts) == 0:
        return None
    return accounts[0]


def get_account():
    interface = get_dbus_account_interface()
    if not interface:
        return None
    signal = bus.get(dbus_endpoint, object_path=interface)
    number = signal.getSelfNumber()
    name = signal.getContactName(number)
    return {'number': number, 'name': name}


def link_account(device_name):
    signal = bus.get(dbus_endpoint)
    device_uri = signal.link(device_name)
    return device_uri


def sendDirectMessage(telephone, message):
    interface = get_dbus_account_interface()
    # TODO: what if no Account?
    if not interface:
        return None
    signal = bus.get(dbus_endpoint, object_path=interface)
    signal.sendMessage(message, [], telephone)


#def sendGroupMessage():
#    message = "Hallo Gruppe!\nGeht das auch, wenns aus ist?"
#    group_name = "kmilletest"
#    groups = getGroups()
#    signal.sendGroupMessage(message, [], groups[group_name])
#
#
#def getGroups():
#    g = {}
#    groups = signal.listGroups()
#    for group in groups:
#        obj, identifier, name = group
#        if len(name) > 0:
#            g[name] = identifier
#            print(name)
#    return g

#sendDirectMessage()
#g = getGroups()
#print(g['kmilletest'])
#sendGrouptMessage()

if __name__ == '__main__':
    telephone = ""
    message = "Hallo du"
    sendDirectMessage(telephone, message)
