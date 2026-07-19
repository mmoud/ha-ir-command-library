# IR Command Library

A privacy-first Home Assistant custom integration that turns learned IR and RF
commands into normal `button` entities. The buttons work in dashboards, GUI
automations, scripts, Assist, and HomeKit Bridge.

The integration supports multiple compatible `remote.*` controllers. BroadLink
is the primary tested use case, but the catalog is controller-agnostic and uses
Home Assistant's standard `remote.learn_command`, `remote.send_command`, and
`remote.delete_command` actions.

## Privacy model

- The library stores only controller entity IDs, area names, appliance names,
  and command names in Home Assistant's private integration storage.
- Learned IR/RF payloads remain owned by the remote integration and are never
  copied into this library, diagnostics, dashboard resources, or this repository.
- Diagnostics contain counts only. They omit entity IDs, areas, device names,
  command names, network addresses, and payloads.
- The integration makes no cloud connection and contains no analytics.

## Installation from a private/custom HACS repository

1. In HACS, open **Integrations**.
2. Add this GitHub repository as a custom repository with category
   **Integration**.
3. Install **IR Command Library** and restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and select
   **IR Command Library**.

For the optional dashboard cards, add this JavaScript module under
**Settings > Dashboards > Resources**:

```text
/api/ir_command_library/ir-command-library-card.js?v=0.1.0
```

## Dashboard cards

Command library:

```yaml
type: custom:ir-command-library-card
```

Learning and management:

```yaml
type: custom:ir-command-manager-card
```

The cards contain no fixed entity IDs. They discover generated command buttons
and compatible remote entities from the current Home Assistant instance.

## Learning a command

The manager card is the easiest path. You can also use the GUI-editable
**IR Command Library: Learn command** action from Developer Tools, scripts, or
automations. Supply:

- a `remote.*` controller;
- the Home Assistant area used for organization;
- a storage-safe appliance name, such as `television`;
- a descriptive command name, such as `power` or `volume_up`.

After learning succeeds, the matching button appears automatically.

## Registering existing commands

If a compatible remote integration already stores a command, use
**Register existing command** with the exact controller, device, and command
names. Registration does not transmit or relearn anything.

## Removing commands

Use **Remove command** and select a generated button. The integration first asks
the remote integration to delete the learned command. It removes the catalog
entry only after that action succeeds.

## Automations and HomeKit

Generated commands are standard Home Assistant button entities. In a GUI
automation, add the **Press button** action and choose a command.

HomeKit Bridge represents Home Assistant buttons as switches. Include the
`button` domain in the bridge. Leaving that domain without a fixed entity filter
allows future learned commands to appear automatically.

## Migration from the prototype To-do catalog

The private release intentionally does not read arbitrary To-do items. Existing
BroadLink commands remain stored by Home Assistant. Use **Register existing
command** once for each old catalog item; no IR/RF payload needs to be copied or
exposed.

## Development checks

```bash
python3 -m compileall -q custom_components
node --check custom_components/ir_command_library/frontend/ir-command-library-card.js
python3 scripts/privacy_check.py
python3 -m unittest discover -s tests -v
```

## Support status

This is an early private backup release. Test command learning and deletion on
a non-critical appliance before relying on it broadly.
