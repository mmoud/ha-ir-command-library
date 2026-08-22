# IR Command Library

A Home Assistant custom integration that turns learned IR and RF commands into
standard `button` entities. Use them from dashboards, automations, scripts,
Assist, and HomeKit Bridge.

The integration supports multiple compatible `remote.*` controllers. BroadLink
is the primary tested use case. The catalog is controller-agnostic and uses
Home Assistant's standard `remote.learn_command`, `remote.send_command`, and
`remote.delete_command` actions, so it can work with other compatible remotes.

## Privacy model

- The library stores controller entity IDs, area names, appliance names, and
  command names in Home Assistant's private integration storage.
- Learned IR/RF payloads remain owned by the remote integration and are never
  copied into this library, diagnostics, dashboard resources, or this repository.
- Diagnostics contain counts only. They omit entity IDs, areas, device names,
  command names, network addresses, and payloads.
- The integration makes no cloud connection and contains no analytics.

## Installation

### HACS

1. In HACS, open **Integrations > Custom repositories**.
2. Add `https://github.com/mmoud/ha-ir-command-library` with category
   **Integration**.
3. Download **IR Command Library** and restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and add
   **IR Command Library**.

### Manual installation

1. Download the latest release source archive.
2. Copy `custom_components/ir_command_library` to Home Assistant's
   `/config/custom_components/` directory.
3. Restart Home Assistant and add **IR Command Library** from
   **Settings > Devices & services**.

For the optional dashboard cards, add this JavaScript module under
**Settings > Dashboards > Resources**:

```text
/api/ir_command_library/ir-command-library-card.js?v=1.0.12
```

The version query string avoids a stale browser cache. Update it when you
install a later release.

## Dashboard cards

Command library:

```yaml
type: custom:ir-command-library-card
```

Learning and management:

```yaml
type: custom:ir-command-manager-card
```

The cards automatically discover generated command buttons and compatible
remote entities; no entity IDs are hard-coded in card YAML.

The controller picker shows only remotes that advertise Home Assistant's
command-learning capability. Media and virtual remotes, such as a HomePod,
are not shown.

## Learning a command

The manager card is the easiest path. You can also use **IR Command Library:
Learn command** from **Developer Tools > Actions**, scripts, or automations.
Provide:

- a `remote.*` controller;
- the Home Assistant area used for organization;
- an appliance name, such as `television`;
- a descriptive command name, such as `power` or `volume_up`.

After learning succeeds, the matching button appears automatically.

## Registering existing commands

If a compatible remote integration already stores a command, use **IR Command
Library: Register existing command** with the exact controller, device, and
command names. Registration neither sends nor relearns the command.

## Removing commands

Use **IR Command Library: Remove command** and select a generated button. The
integration deletes the learned command from the remote first, then removes its
catalog entry only if that succeeds.

## Automations and HomeKit

Generated commands are standard Home Assistant button entities. In an
automation or script, use the built-in **Press button** action (`button.press`)
and select the command. There is intentionally no separate send-command action
for each saved IR command.

HomeKit Bridge represents Home Assistant buttons as switches. Include the
`button` domain in the bridge. Leaving that domain without a fixed entity filter
allows future learned commands to appear automatically.

## Migrating from the original prototype

This integration does not read arbitrary To-do items during normal operation.
If you used the original `codex_ir_commands` prototype, keep it and its To-do
list installed during migration:

1. Install this integration, restart Home Assistant, and add **IR Command
   Library** from **Settings > Devices & services**.
2. In Developer Tools, run **IR Command Library: Import legacy To-do catalog**
   and select the original `todo.*` entity (normally the IR Command Library
   catalog).
3. The action copies only valid `controller | area | device | command` metadata
   into this integration's private catalog. Older three-part
   `controller | device | command` records are grouped under an `Imported`
   area. It does not transmit, relearn, modify, or delete any command.
4. Test the generated buttons. Once the command count and operation are
   confirmed, remove the old prototype and its dashboard resources.

The import is idempotent: it is safe to run again, and existing commands are
not duplicated. Existing BroadLink commands remain stored by Home Assistant;
no IR/RF payload needs to be copied or exposed.

If an early migration left duplicate devices in the **Imported** area, run
**IR Command Library: Clean up legacy orphaned devices**. It removes only the
old orphaned device records and refuses to remove a record that still has
entities. It does not send, relearn, or delete IR/RF payloads.

## Contributing and releases

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a change. Before a
release, run the checks below from a clean checkout. The privacy check scans the
working tree and reachable Git history for common Home Assistant secrets and
personal-network artifacts.

```bash
python3 scripts/privacy_check.py
python3 -m compileall -q custom_components
python3 -m unittest discover -s tests -v
node --check custom_components/ir_command_library/frontend/ir-command-library-card.js
```

Do not upload Home Assistant backups, `.storage` folders, learned-code files,
diagnostics archives, private-dashboard screenshots, or learned IR/RF payloads.

## Support status

Test learning and deletion on a non-critical appliance before relying on it for
daily use.
