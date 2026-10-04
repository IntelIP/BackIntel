import Foundation
import Security

// Values travel through stdin/stdout captured by the launcher, never process arguments.
let service = "BackIntel Analysis " + CommandLine.arguments[2]
let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                         kSecAttrService as String: service,
                         kSecAttrAccount as String: "local"]
if CommandLine.arguments[1] == "set" {
    let value = FileHandle.standardInput.readDataToEndOfFile()
    let status = SecItemUpdate(query as CFDictionary, [kSecValueData as String: value] as CFDictionary)
    if status == errSecItemNotFound {
        var item = query
        item[kSecValueData as String] = value
        item[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { exit(1) }
    } else if status != errSecSuccess { exit(1) }
} else {
    var item = query
    item[kSecReturnData as String] = true
    var result: CFTypeRef?
    guard SecItemCopyMatching(item as CFDictionary, &result) == errSecSuccess,
          let data = result as? Data else { exit(1) }
    FileHandle.standardOutput.write(data)
}
