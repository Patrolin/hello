const std = @import("std");

pub fn main() !void {
    const stdout = std.io.getStdOut().outStream();
    try stdout.print("hello world\n", .{});
}
