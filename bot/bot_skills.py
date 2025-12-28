from models import MinecraftBuild


def place_block(bot, block_type, x, y, z, direction=False):
    valid_directions = {"north", "south", "east", "west"}

    # Format the command and send it using bot.chat instead of print
    if direction in valid_directions:
        # print(direction)
        command = f"/setblock {x} {y} {z} {block_type}[facing={direction}]"
    else:
        command = f"/setblock {x} {y} {z} {block_type}"

    bot.chat(command)


def build_from_json(bot, json_data):
    # with open(file, 'r') as file:
    #     json_data = file.read()
    pos = bot.entity.position
    base_x = int(pos.x)
    base_y = int(pos.y)
    base_z = int(pos.z)
    # Parse the JSON data into a MinecraftBuild instance
    minecraft_build = MinecraftBuild.model_validate(
        json_data
    )  # class that parses and holds json using BaseModel
    for block in minecraft_build.blocks:
        direction = getattr(block, "facing", False)
        place_block(
            bot,
            block.block_type,
            block.x + base_x,
            block.y + base_y,
            block.z + base_z,
            direction,
        )
